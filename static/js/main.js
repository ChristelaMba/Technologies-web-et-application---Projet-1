
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


const formulaireReservation = document.querySelector(".reservation-form");

if (formulaireReservation) {
    const champDate = document.querySelector("#date");
    const champHeure = document.querySelector("#heure");
    const messageCreneaux = document.querySelector("#message-creneaux");

    async function chargerCreneaux() {
        champHeure.innerHTML = "";
        champHeure.disabled = true;

        const optionInitiale = document.createElement("option");
        optionInitiale.value = "";
        optionInitiale.textContent = "Chargement des créneaux...";
        champHeure.appendChild(optionInitiale);

        const dateChoisie = champDate.value;

        if (!dateChoisie) {
            optionInitiale.textContent = "Choisissez d'abord une date";
            messageCreneaux.textContent =
                "Sélectionnez une date pour consulter les disponibilités.";
            return;
        }

        try {
            const medecinId = formulaireReservation.dataset.medecinId;
            const reponse = await fetch(
                `/api/creneaux?medecin_id=${medecinId}&date=${encodeURIComponent(dateChoisie)}`
            );

            const donnees = await reponse.json();

            champHeure.innerHTML = "";

            if (!reponse.ok || donnees.creneaux.length === 0) {
                const optionVide = document.createElement("option");
                optionVide.value = "";
                optionVide.textContent = "Aucun créneau disponible";
                champHeure.appendChild(optionVide);

                messageCreneaux.textContent = donnees.message;
                return;
            }

            const optionInitiale = document.createElement("option");
            optionInitiale.value = "";
            optionInitiale.textContent = "Choisissez une heure";
            champHeure.appendChild(optionInitiale);

            donnees.creneaux.forEach(function (heure) {
                const option = document.createElement("option");
                option.value = heure;
                option.textContent = heure;
                champHeure.appendChild(option);
            });

            champHeure.disabled = false;
            messageCreneaux.textContent =
                "Choisissez l'un des créneaux disponibles.";
        } catch (erreur) {
            champHeure.innerHTML = "";

            const optionErreur = document.createElement("option");
            optionErreur.value = "";
            optionErreur.textContent = "Disponibilités indisponibles";
            champHeure.appendChild(optionErreur);

            messageCreneaux.textContent =
                "Impossible de charger les créneaux. Réessayez.";
        }
    }

    champDate.addEventListener("change", chargerCreneaux);

    if (champDate.value) {
        chargerCreneaux();
    }
}
