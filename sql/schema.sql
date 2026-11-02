CREATE TABLE IF NOT EXISTS dim_agence (
id_agence SERIAL PRIMARY KEY,
agence VARCHAR(100) UNIQUE,
ville VARCHAR(100),
responsable VARCHAR(100),
objectif NUMERIC
);


CREATE TABLE IF NOT EXISTS dim_agent (
id_agent SERIAL PRIMARY KEY,
agent VARCHAR(100),
id_agence INT REFERENCES dim_agence,
objectif NUMERIC,
statut VARCHAR(30)
);


CREATE TABLE IF NOT EXISTS dim_client (
id_client SERIAL PRIMARY KEY,
client VARCHAR(150),
categorie VARCHAR(50),
zone VARCHAR(100),
date_inscription DATE
);


CREATE TABLE IF NOT EXISTS dim_produit (
id_produit SERIAL PRIMARY KEY,
produit VARCHAR(150),
categorie VARCHAR(80),
prix NUMERIC,
marge NUMERIC
);


CREATE TABLE IF NOT EXISTS dim_date (
id_temps INT PRIMARY KEY,
date DATE,
jour INT,
mois INT,
trimestre INT,
annee INT
);


CREATE TABLE IF NOT EXISTS fait_vente (
id_vente SERIAL PRIMARY KEY,
id_temps INT REFERENCES dim_date,
id_agence INT REFERENCES dim_agence,
id_agent INT REFERENCES dim_agent,
id_client INT REFERENCES dim_client,
id_produit INT REFERENCES dim_produit,
quantite INT,
prix_unitaire NUMERIC,
montant NUMERIC
);

CREATE TABLE IF NOT EXISTS utilisateur (
id_utilisateur SERIAL PRIMARY KEY,
nom VARCHAR(100) NOT NULL,
login VARCHAR(50) NOT NULL UNIQUE,
mot_de_passe_hash VARCHAR(255) NOT NULL,
role VARCHAR(20) NOT NULL CHECK (role IN ('administrateur','responsable','agent')),
id_agence INT REFERENCES dim_agence(id_agence)
);


CREATE INDEX IF NOT EXISTS idx_fait_vente_temps ON fait_vente(id_temps);
CREATE INDEX IF NOT EXISTS idx_fait_vente_agence ON fait_vente(id_agence);
CREATE INDEX IF NOT EXISTS idx_fait_vente_agent ON fait_vente(id_agent);
-- Journal d'audit (v3)
CREATE TABLE IF NOT EXISTS journal_audit (
    id SERIAL PRIMARY KEY,
    date_action TIMESTAMP DEFAULT now(),
    id_utilisateur INT REFERENCES utilisateur(id_utilisateur) ON DELETE SET NULL,
    action VARCHAR(50) NOT NULL,
    detail TEXT
);
