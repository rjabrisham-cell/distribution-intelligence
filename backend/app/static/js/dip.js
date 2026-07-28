/* =========================================================
   DIP — Global UI
   ========================================================= */

document.addEventListener("DOMContentLoaded", function () {

    /*
     * Global initialization
     */

    console.log(
        "Distribution Intelligence Platform initialized."
    );


    /*
     * Auto-hide flash/toast messages
     */

    const alerts = document.querySelectorAll(
        ".dip-alert[data-auto-dismiss='true']"
    );

    alerts.forEach(function (alert) {

        setTimeout(function () {

            alert.style.opacity = "0";

            setTimeout(function () {
                alert.remove();
            }, 300);

        }, 5000);

    });


    /*
     * Prevent accidental double form submission
     */

    const forms = document.querySelectorAll(
        "form[data-prevent-double-submit='true']"
    );

    forms.forEach(function (form) {

        form.addEventListener(
            "submit",
            function () {

                const submitButton =
                    form.querySelector(
                        "button[type='submit']"
                    );

                if (!submitButton) {
                    return;
                }

                submitButton.disabled = true;

                submitButton.dataset.originalText =
                    submitButton.innerHTML;

                submitButton.innerHTML =
                    "در حال پردازش...";

            }
        );

    });

});