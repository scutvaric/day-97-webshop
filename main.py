from flask import Flask, abort, render_template, redirect, url_for, flash, request
from flask_bootstrap import Bootstrap5
from flask_ckeditor import CKEditor
from flask_login import UserMixin, login_user, LoginManager, current_user, logout_user, login_required
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship, DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String, ForeignKey, text
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from forms import AddItem, RegisterForm, LoginForm
import os
from dotenv import load_dotenv

load_dotenv("variables.env")
import smtplib
import stripe

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('FLASK_KEY')
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')
stripe.api_key = os.environ.get('STRIPE_API_KEY')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
UPLOAD_FOLDER = "static/uploads"
MY_DOMAIN = "http://127.0.0.1:5000"

ckeditor = CKEditor(app)
Bootstrap5(app)

# Configure Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    return db.get_or_404(User, user_id)


# CREATE DATABASE
class Base(DeclarativeBase):
    pass


# ✅ Add timeout and check_same_thread
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    "DB_URI",
    "sqlite:///items.db?check_same_thread=False&timeout=30"
)
db = SQLAlchemy(model_class=Base)
db.init_app(app)


class Item(db.Model):
    __tablename__ = "items"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(250), nullable=False)
    description: Mapped[str] = mapped_column(String(1000), nullable=False)
    image: Mapped[str] = mapped_column(String(500), nullable=False)  # URL or file path
    price: Mapped[float] = mapped_column(db.Float, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    cart_items = relationship("CartItem", back_populates="item")


class User(UserMixin, db.Model):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(100), unique=True)
    password: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)

    cart_items = relationship("CartItem", back_populates="user", cascade="all, delete")


class CartItem(db.Model):
    __tablename__ = "cart_items"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    item_id: Mapped[int] = mapped_column(Integer, ForeignKey("items.id"))
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    user = relationship("User", back_populates="cart_items")
    item = relationship("Item", back_populates="cart_items")


with app.app_context():
    db.create_all()
    # Run PRAGMA directly on the engine connection (outside session transaction)
    with db.engine.connect() as conn:
        conn.execute(text("PRAGMA journal_mode=WAL;"))


# Create an admin-only decorator
def admin_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.id != 1:
            return abort(403)
        return f(*args, **kwargs)

    return decorated_function


@app.route('/register', methods=["GET", "POST"])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        result = db.session.execute(db.select(User).where(User.email == form.email.data))
        user = result.scalar()
        if user:
            flash("You've already signed up with that email, log in instead!")
            return redirect(url_for('login'))

        hash_and_salted_password = generate_password_hash(
            form.password.data,
            method='pbkdf2:sha256',
            salt_length=8
        )
        new_user = User(
            email=form.email.data,
            name=form.name.data,
            password=hash_and_salted_password,
        )
        db.session.add(new_user)
        db.session.commit()
        login_user(new_user)
        return redirect(url_for("home"))
    return render_template("register.html", form=form, current_user=current_user)


@app.route('/login', methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        password = form.password.data
        result = db.session.execute(db.select(User).where(User.email == form.email.data))
        user = result.scalar()
        if not user:
            flash("That email does not exist, please try again.")
            return redirect(url_for('login'))
        elif not check_password_hash(user.password, password):
            flash('Password incorrect, please try again.')
            return redirect(url_for('login'))
        else:
            login_user(user)
            return redirect(url_for('home'))
    return render_template("login.html", form=form, current_user=current_user)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('home'))


@app.route('/')
def home():
    result = db.session.execute(db.select(Item))
    items = result.scalars().all()
    updated_item = request.args.get("updated_item", type=int)
    return render_template("index.html",
                           all_items=items,
                           current_user=current_user,
                           updated_item=updated_item)


@app.route("/new-item", methods=["GET", "POST"])
@admin_only
def add_new_item():
    form = AddItem()
    if form.image.data:
        filename = secure_filename(form.image.data.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        form.image.data.save(filepath)
        image_path = f"/static/uploads/{filename}"
    else:
        image_path = ""

    if form.validate_on_submit():
        new_item = Item(
            name=form.name.data,
            description=form.description.data,
            image=image_path,
            price=form.price.data,
            quantity=form.quantity.data
        )
        db.session.add(new_item)
        db.session.commit()
        return redirect(url_for("home"))
    return render_template("make-item.html", form=form, current_user=current_user)


@app.route("/add-to-cart/<int:item_id>", methods=["POST"])
def add_to_cart(item_id):
    if not current_user.is_authenticated:
        flash("Please log in to add items to your cart.", "warning")
        return redirect(url_for("login"))

    item = Item.query.get_or_404(item_id)
    quantity = int(request.form.get("quantity", 1))

    existing = CartItem.query.filter_by(user_id=current_user.id, item_id=item.id).first()
    if existing:
        existing.quantity += quantity
    else:
        new_cart_item = CartItem(user_id=current_user.id, item_id=item.id, quantity=quantity)
        db.session.add(new_cart_item)

    db.session.commit()
    flash(f"{item.name} added to your cart!", "success")
    return redirect(url_for("home", updated_item=item.id))


@app.route("/edit-item/<int:item_id>", methods=["GET", "POST"])
@admin_only
def edit_item(item_id):
    item = db.get_or_404(Item, item_id)
    edit_form = AddItem(
        name=item.name,
        description=item.description,
        image=item.image,
        price=item.price,
        quantity=item.quantity
    )

    if edit_form.validate_on_submit():
        item.name = edit_form.name.data
        item.description = edit_form.description.data
        item.price = edit_form.price.data
        item.quantity = edit_form.quantity.data

        if edit_form.image.data:
            file = edit_form.image.data
            if hasattr(file, "filename") and file.filename != "":
                filename = secure_filename(file.filename)
                filepath = os.path.join(UPLOAD_FOLDER, filename)
                file.save(filepath)
                item.image = filepath

        db.session.commit()
        flash(f"Item '{item.name}' was updated successfully!", "success")
        return redirect(url_for("home", updated_item=item.id))

    return render_template("make-item.html", form=edit_form, is_edit=True, current_user=current_user)


@app.route("/delete/<int:item_id>")
@admin_only
def delete_item(item_id):
    item_to_delete = db.get_or_404(Item, item_id)
    db.session.delete(item_to_delete)
    db.session.commit()
    return redirect(url_for('home'))


@app.route("/about")
def about():
    return render_template("about.html", current_user=current_user)


MAIL_ADDRESS = os.environ.get("EMAIL_KEY")
MAIL_APP_PW = os.environ.get("PASSWORD_KEY")


@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        data = request.form
        send_email(data["name"], data["email"], data["phone"], data["message"])
        return render_template("contact.html", msg_sent=True)
    return render_template("contact.html", msg_sent=False)


def send_email(name, email, phone, message):
    email_message = f"Subject:New Message\n\nName: {name}\nEmail: {email}\nPhone: {phone}\nMessage:{message}"
    with smtplib.SMTP("smtp.gmail.com") as connection:
        connection.starttls()
        connection.login(MAIL_ADDRESS, MAIL_APP_PW)
        connection.sendmail(MAIL_ADDRESS, MAIL_ADDRESS, email_message)


@app.route("/api/cart")
@login_required
def api_cart():
    cart_items = (
        db.session.query(CartItem)
        .filter_by(user_id=current_user.id)
        .join(Item)
        .all()
    )

    cart_data = []
    total = 0

    for ci in cart_items:
        item_data = {
            "id": ci.item.id,
            "name": ci.item.name,
            "price": ci.item.price,
            "quantity": ci.quantity,
            "subtotal": ci.item.price * ci.quantity,
            "image": ci.item.image,
        }
        cart_data.append(item_data)
        total += item_data["subtotal"]

    return {
        "items": cart_data,
        "total": total
    }


@app.route("/api/cart/remove/<int:item_id>", methods=["DELETE"])
@login_required
def api_remove_cart_item(item_id):
    cart_item = CartItem.query.filter_by(user_id=current_user.id, item_id=item_id).first()
    if cart_item:
        if cart_item.quantity > 1:
            cart_item.quantity -= 1  # ✅ only reduce by 1
        else:
            db.session.delete(cart_item)  # ✅ remove row if it was the last one
        db.session.commit()
        return {"success": True, "remaining": cart_item.quantity if cart_item in db.session else 0}
    return {"success": False, "error": "Item not found"}, 404


# ✅ Clean up sessions after each request
@app.teardown_appcontext
def shutdown_session(exception=None):
    db.session.remove()


@app.route('/create-checkout-session', methods=['POST'])
@login_required
def create_checkout_session():
    # 1. Get the user's cart
    cart_items = (
        db.session.query(CartItem)
        .filter_by(user_id=current_user.id)
        .join(Item)
        .all()
    )

    if not cart_items:
        return {"error": "Cart is empty"}, 400

    # 2. Build Stripe line_items
    line_items = []
    for ci in cart_items:
        line_items.append({
            'price_data': {
                'currency': 'usd',  # or your currency
                'unit_amount': int(round(ci.item.price * 100)),  # cents
                'product_data': {
                    'name': ci.item.name,
                    # Only include images if they are full URLs
                    # 'images': [ci.item.image] if ci.item.image.startswith("http") else [],
                },
            },
            'quantity': ci.quantity,
        })

    try:
        # 3. Create checkout session
        checkout_session = stripe.checkout.Session.create(
            line_items=line_items,
            mode='payment',
            success_url=MY_DOMAIN + '/success',
            cancel_url=MY_DOMAIN + '/cancel',
            customer_email=current_user.email,  # optional
        )
    except Exception as e:
        return {"error": str(e)}, 500

    # 4. Redirect user to Stripe Checkout
    return {"url": checkout_session.url}


@app.route("/success")
def success():
    return "<h1>Payment successful!</h1>"


@app.route("/cancel")
def cancel():
    return "<h1>Payment cancelled.</h1>"


if __name__ == "__main__":
    # ✅ Disable threading to avoid SQLite race conditions
    app.run(debug=False, port=5000, threaded=False)
