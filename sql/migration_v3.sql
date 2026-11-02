-- À exécuter UNE fois sur une base existante (créée avec la v1 ou la v2)
CREATE TABLE IF NOT EXISTS journal_audit (
    id SERIAL PRIMARY KEY,
    date_action TIMESTAMP DEFAULT now(),
    id_utilisateur INT REFERENCES utilisateur(id_utilisateur) ON DELETE SET NULL,
    action VARCHAR(50) NOT NULL,
    detail TEXT
);
