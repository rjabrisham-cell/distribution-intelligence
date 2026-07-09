document.addEventListener("DOMContentLoaded", () => {

    Dashboard.init();

});

const Dashboard = {

    init() {

        this.bindButtons();

        this.loadCounters();

        this.refreshProjectStatus();

        this.autoRefresh();

    },

    bindButtons() {

        const runBtn = document.querySelector("#runDistribution");

        if (runBtn) {

            runBtn.addEventListener("click", () => {

                Dashboard.runDistribution();

            });

        }

        const mapBtn = document.querySelector("#openMap");

        if (mapBtn) {

            mapBtn.addEventListener("click", () => {

                window.location.href = "/map";

            });

        }

        const newProjectBtn = document.querySelector("#newProject");

        if (newProjectBtn) {

            newProjectBtn.addEventListener("click", () => {

                window.location.href = "/projects/new";

            });

        }

    },

    async runDistribution() {

        try {

            Dashboard.loading(true);

            const response = await fetch("/distribution/run", {

                method: "POST"

            });

            const result = await response.json();

            Dashboard.loading(false);

            Dashboard.toast(result.message || "Distribution Started","success");

        }

        catch(e){

            Dashboard.loading(false);

            Dashboard.toast("Distribution Engine Error","danger");

        }

    },

    async loadCounters(){

        try{

            const response=await fetch("/api/dashboard");

            if(!response.ok) return;

            const data=await response.json();

            Dashboard.setValue("kpiProjects",data.projects);

            Dashboard.setValue("kpiCompanies",data.companies);

            Dashboard.setValue("kpiOrders",data.orders);

            Dashboard.setValue("kpiVehicles",data.vehicles);

        }

        catch(e){

            console.log(e);

        }

    },

    async refreshProjectStatus(){

        try{

            const response=await fetch("/api/projects/status");

            if(!response.ok) return;

            const rows=await response.json();

            rows.forEach(item=>{

                const badge=document.querySelector("#status-"+item.id);

                if(badge){

                    badge.innerHTML=item.status;

                    badge.className="project-status status-"+item.status.toLowerCase();

                }

            });

        }

        catch(e){

            console.log(e);

        }

    },

    autoRefresh(){

        setInterval(()=>{

            Dashboard.refreshProjectStatus();

        },30000);

    },

    loading(state){

        const overlay=document.querySelector("#loadingOverlay");

        if(!overlay) return;

        overlay.style.display=state?"flex":"none";

    },

    setValue(id,value){

        const el=document.getElementById(id);

        if(el){

            el.innerHTML=value;

        }

    },

    toast(message,type="success"){

        const toast=document.createElement("div");

        toast.className="toast-message "+type;

        toast.innerHTML=message;

        document.body.appendChild(toast);

        setTimeout(()=>{

            toast.classList.add("show");

        },100);

        setTimeout(()=>{

            toast.classList.remove("show");

            setTimeout(()=>{

                toast.remove();

            },300);

        },3000);

    }

};