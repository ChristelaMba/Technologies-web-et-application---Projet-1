
const boutonMenu = document.querySelector("#menu-toggle");
const liensNavigation = document.querySelector("#nav-links");

if (boutonMenu && liensNavigation) {
    boutonMenu.addEventListener("click", () => {
        const menuOuvert = liensNavigation.classList.toggle("is-open");

        boutonMenu.setAttribute("aria-expanded", String(menuOuvert));
        boutonMenu.setAttribute(
            "aria-label",
            menuOuvert ? "Fermer le menu" : "Ouvrir le menu"
        );
    });
}



const filtreSpecialite = document.querySelector("#filtre-specialite");

if (filtreSpecialite) {
    const cartesMedecins = document.querySelectorAll(".doctor-card");
    const messageAucunResultat = document.querySelector("#aucun-resultat");

    filtreSpecialite.addEventListener("change", function () {
        let nombreVisible = 0;

        cartesMedecins.forEach(function (carte) {
            const correspond =
                filtreSpecialite.value === "toutes" ||
                carte.dataset.specialite === filtreSpecialite.value;

            carte.hidden = !correspond;

            if (correspond) {
                nombreVisible++;
            }
        });

        if (messageAucunResultat) {
            messageAucunResultat.hidden = nombreVisible > 0;
        }
    });
}
