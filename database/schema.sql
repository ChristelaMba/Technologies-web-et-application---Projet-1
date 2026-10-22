
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS medecins (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nom TEXT NOT NULL,
    specialite TEXT NOT NULL,
    photo TEXT,
    jours_consultation TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS patients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nom TEXT NOT NULL,
    prenom TEXT NOT NULL,
    telephone TEXT NOT NULL UNIQUE,
    date_naissance TEXT NOT NULL,
    ville TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS rendez_vous (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER NOT NULL,
    medecin_id INTEGER NOT NULL,
    date TEXT NOT NULL,
    heure TEXT NOT NULL,
    motif TEXT NOT NULL,
    statut TEXT NOT NULL DEFAULT 'prévu'
        CHECK (statut IN ('prévu', 'effectué', 'annulé')),
    date_prise TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),

    FOREIGN KEY (patient_id) REFERENCES patients(id),
    FOREIGN KEY (medecin_id) REFERENCES medecins(id),

    UNIQUE (medecin_id, date, heure)
);

CREATE TABLE IF NOT EXISTS administrateurs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    identifiant TEXT NOT NULL UNIQUE,
    mot_de_passe_hash TEXT NOT NULL
);
