document.addEventListener("DOMContentLoaded", function () {
    DashboardPage.init();
});

const DashboardPage = {
    init() {
        this.bindEvents();
        this.loadCounters();
        this.setActiveSidebar();
    },

    bindEvents() {
        const runBtn = document.getElementById("runDistribution");
        const mapBtn = document.getElementById("openMap");
        const projectBtn = document.getElementById("newProject");

        if (runBtn) {
            runBtn.addEventListener("click", () => this.runDistributionMock());
        }

        if (mapBtn) {
            mapBtn.addEventListener("click", () => {
                window.open("http://localhost:8082/", "_blank");
            });
        }

        if (projectBtn) {
            projectBtn.addEventListener("click", () => {
                window.location.href = "/projects/new";
            });
        }
    },

    setActiveSidebar() {
        const links = document.querySelectorAll(".sidebar-link");
        const currentPath = window.location.pathname;

        links.forEach((link) => {
            const href = link.getAttribute("href");
            if (href === currentPath) {
                link.classList.add("active");
            } else if (href !== "http://localhost:8082/") {
                link.classList.remove("active");
            }
        });
    },

    async loadCounters() {
        const fallbackData = {
            projects: 12,
            companies: 8,
            orders: 1540,
            vehicles: 47
        };

        try {
            const response = await fetch("/api/dashboard", {
                method: "GET",
                headers: {
                    "Content-Type": "application/json"
                }
            });

            if (!response.ok) {
                this.fillCounters(fallbackData);
                return;
            }

            const data = await response.json();

            this.fillCounters({
                projects: data.projects ?? fallbackData.projects,
                companies: data.companies ?? fallbackData.companies,
                orders: data.orders ?? fallbackData.orders,
                vehicles: data.vehicles ?? fallbackData.vehicles
            });
        } catch (error) {
            this.fillCounters(fallbackData);
        }
    },

    fillCounters(data) {
        this.setText("kpiProjects", data.projects);
        this.setText("kpiCompanies", data.companies);
        this.setText("kpiOrders", data.orders);
        this.setText("kpiVehicles", data.vehicles);
    },

    async runDistributionMock() {
        this.toggleLoading(true);

        try {
            let message = "اجرای توزیع آزمایشی با موفقیت انجام شد.";

            try {
                const response = await fetch("/distribution/run", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    }
                });

                if (response.ok) {
                    const result = await response.json();
                    if (result && result.message) {
                        message = result.message;
                    }
                }
            } catch (innerError) {
                // Backend route may not exist yet in Sprint 1
            }

            setTimeout(() => {
                this.toggleLoading(false);
                this.showToast(message, "success");
            }, 1200);
        } catch (error) {
            this.toggleLoading(false);
            this.showToast("در اجرای توزیع خطایی رخ داد.", "error");
        }
    },

    toggleLoading(show) {
        const overlay = document.getElementById("loadingOverlay");
        if (!overlay) return;

        if (show) {
            overlay.classList.remove("hidden");
        } else {
            overlay.classList.add("hidden");
        }
    },

    setText(id, value) {
        const el = document.getElementById(id);
        if (el) {
            el.textContent = value;
        }
    },

    showToast(message, type = "info") {
        const container = document.getElementById("globalToastContainer");
        if (!container) return;

        const toast = document.createElement("div");
        toast.className = `toast toast-${type}`;
        toast.textContent = message;

        container.appendChild(toast);

        setTimeout(() => {
            toast.style.opacity = "0";
            toast.style.transform = "translateY(10px)";
            toast.style.transition = "all 0.3s ease";
        }, 2800);

        setTimeout(() => {
            toast.remove();
        }, 3200);
    }
};
