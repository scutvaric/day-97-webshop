/*!
* Start Bootstrap - Clean Blog v6.0.9 (https://startbootstrap.com/theme/clean-blog)
* Copyright 2013-2023 Start Bootstrap
* Licensed under MIT (https://github.com/StartBootstrap/startbootstrap-clean-blog/blob/master/LICENSE)
*/
window.addEventListener('DOMContentLoaded', () => {
    let scrollPos = 0;
    const mainNav = document.getElementById('mainNav');
    const headerHeight = mainNav.clientHeight;
    window.addEventListener('scroll', function() {
        const currentTop = document.body.getBoundingClientRect().top * -1;
        if ( currentTop < scrollPos) {
            // Scrolling Up
            if (currentTop > 0 && mainNav.classList.contains('is-fixed')) {
                mainNav.classList.add('is-visible');
            } else {
                console.log(123);
                mainNav.classList.remove('is-visible', 'is-fixed');
            }
        } else {
            // Scrolling Down
            mainNav.classList.remove(['is-visible']);
            if (currentTop > headerHeight && !mainNav.classList.contains('is-fixed')) {
                mainNav.classList.add('is-fixed');
            }
        }
        scrollPos = currentTop;
    });
})

  function updateCount(fieldId, maxLength) {
    const input = document.getElementById(fieldId);
    const counter = document.getElementById(fieldId + "-count");

    const remaining = maxLength - input.value.length;
    counter.textContent = remaining + " characters left";

    // Optional: turn red when exceeded
    if (remaining < 0) {
      counter.classList.remove("text-muted");
      counter.classList.add("text-danger");
    } else {
      counter.classList.remove("text-danger");
      counter.classList.add("text-muted");
    }
  }

  // Initialize counters on page load (important for edit mode)
document.addEventListener("DOMContentLoaded", function () {
    updateCount("name", 50);
    updateCount("description", 80);
  });

document.addEventListener("DOMContentLoaded", function () {
    const flashMessages = document.querySelectorAll(".alert");
    flashMessages.forEach(function (msg) {
      setTimeout(() => {
        let alert = new bootstrap.Alert(msg);
        alert.close();
      }, 3000); // 3 seconds
    });
  });
document.addEventListener("DOMContentLoaded", () => {
    const cartSidebar = document.getElementById("cart-sidebar");
    const cartToggle = document.getElementById("cart-toggle");
    const cartClose = document.getElementById("cart-close");
    const cartItemsList = document.getElementById("cart-items");
    const cartTotal = document.getElementById("cart-total");
    const cartCount = document.getElementById("cart-count");

    function loadCart() {
        fetch("/api/cart")
            .then(res => res.json())
            .then(data => {
                cartItemsList.innerHTML = "";
                let total = 0;
                let count = 0;

                data.items.forEach(item => {
                    const li = document.createElement("li");
                    li.classList.add("list-group-item", "d-flex", "align-items-center");

                    li.innerHTML = `
                        <img src="${item.image}" alt="${item.name}"
                             style="width:50px;height:50px;object-fit:cover;margin-right:10px;border-radius:6px;">
                        <div class="flex-grow-1">
                            <strong>${item.name}</strong><br>
                            $${item.price.toFixed(2)} × ${item.quantity}
                        </div>
                        <span class="badge bg-primary rounded-pill me-2">
                            $${item.subtotal.toFixed(2)}
                        </span>
                        <button class="btn btn-sm btn-danger remove-btn" data-id="${item.id}">
                            <i class="fas fa-trash"></i>
                        </button>
                    `;

                    cartItemsList.appendChild(li);

                    total += item.subtotal;
                    count += item.quantity;
                });

                cartTotal.textContent = total.toFixed(2);
                cartCount.textContent = count;

                // Enable delete buttons
                document.querySelectorAll(".remove-btn").forEach(btn => {
                    btn.addEventListener("click", () => {
                        const id = btn.dataset.id;
                        fetch(`/api/cart/remove/${id}`, { method: "DELETE" })
                            .then(res => res.json())
                            .then(result => {
                                if (result.success) {
                                    loadCart(); // reload after deletion
                                }
                            })
                            .catch(err => console.error("Error removing item:", err));
                    });
                });
            })
            .catch(err => console.error("Error loading cart:", err));
    }

    // ✅ Load cart count on page load
    loadCart();

    cartToggle.addEventListener("click", () => {
        cartSidebar.classList.add("visible");
        loadCart();
    });

    cartClose.addEventListener("click", () => {
        cartSidebar.classList.remove("visible");
    });

    // ✅ Also listen for "Add to Cart" form submits
    document.querySelectorAll("form[action^='/add-to-cart/']").forEach(form => {
        form.addEventListener("submit", (e) => {
            // Let the form submit normally, then refresh cart count
            setTimeout(loadCart, 500);
        });
    });
});

document.addEventListener("DOMContentLoaded", () => {
    const checkoutButton = document.getElementById("checkout-button");
    if (checkoutButton) {
        checkoutButton.addEventListener("click", function () {
            console.log("✅ Checkout button clicked!");

            fetch("/create-checkout-session", {
    method: "POST",
    headers: { "Content-Type": "application/json" }
})
            .then(response => response.json())
            .then(data => {
                if (data.url) {
                    window.location.href = data.url; // 🚀 redirect to Stripe Checkout
                } else {
                    console.error("Stripe error:", data.error);
                    alert("Checkout failed: " + data.error);
                }
            })
            .catch(err => {
                console.error("Fetch error:", err);
            });
        });
    }
});