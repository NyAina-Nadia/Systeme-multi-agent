"""Chargement d'un jeu de ventes normalisé dans le modèle en étoile PostgreSQL."""
import pandas as pd
from sqlalchemy import text
from app.db import engine


def _nouveaux(conn, table, cle, df, colonnes_cle):
    """Insère uniquement les lignes absentes de la table (comparaison sur colonnes_cle)."""
    existants = pd.read_sql(f"SELECT {', '.join(colonnes_cle)} FROM {table}", conn)
    fusion = df.merge(existants, on=colonnes_cle, how="left", indicator=True)
    a_inserer = fusion[fusion["_merge"] == "left_only"].drop(columns="_merge")
    if len(a_inserer):
        a_inserer[df.columns].to_sql(table, conn, if_exists="append", index=False)
    return len(a_inserer)


def charger_agence(ventes: pd.DataFrame, ville: str = "", responsable: str = "",
                   objectif: float = 0, remplacer: bool = True) -> dict:
    """
    Charge les ventes (schéma cible) d'UNE agence.
    - crée l'agence si elle n'existe pas, sinon met à jour ses informations ;
    - ajoute les nouveaux produits / clients / agents / dates ;
    - remplace les ventes existantes de cette agence (remplacer=True) -> ré-import sans doublon.
    """
    if ventes.empty:
        raise ValueError("Aucune ligne valide à charger.")
    noms = ventes["agence"].unique()
    if len(noms) != 1:
        raise ValueError("Le chargement doit porter sur une seule agence à la fois.")
    agence = noms[0]

    with engine.begin() as conn:
        # 1) Agence
        id_agence = conn.execute(text("SELECT id_agence FROM dim_agence WHERE agence = :a"),
                                 {"a": agence}).scalar()
        creee = id_agence is None
        if creee:
            id_agence = conn.execute(text(
                "INSERT INTO dim_agence (agence, ville, responsable, objectif) "
                "VALUES (:a, :v, :r, :o) RETURNING id_agence"),
                {"a": agence, "v": ville or agence, "r": responsable or "À définir",
                 "o": objectif or 0}).scalar()
        else:
            conn.execute(text(
                "UPDATE dim_agence SET ville = COALESCE(NULLIF(:v,''), ville), "
                "responsable = COALESCE(NULLIF(:r,''), responsable), "
                "objectif = CASE WHEN :o > 0 THEN :o ELSE objectif END "
                "WHERE id_agence = :i"),
                {"v": ville, "r": responsable, "o": objectif or 0, "i": id_agence})

        # 2) Dimensions
        dim_produit = ventes[["produit", "categorie"]].drop_duplicates().assign(prix=0, marge=0)
        _nouveaux(conn, "dim_produit", "produit", dim_produit, ["produit", "categorie"])

        dim_client = (ventes[["client"]].drop_duplicates()
                      .assign(categorie="Non classé", zone="Non renseignée"))
        _nouveaux(conn, "dim_client", "client", dim_client, ["client"])

        dim_agent = (ventes[["commercial"]].drop_duplicates()
                     .rename(columns={"commercial": "agent"})
                     .assign(id_agence=id_agence, objectif=0, statut="Actif"))
        _nouveaux(conn, "dim_agent", "agent", dim_agent, ["agent", "id_agence"])

        dates = pd.DataFrame({"date": pd.to_datetime(ventes["date"].dt.normalize().unique())})
        dates["id_temps"] = dates["date"].dt.strftime("%Y%m%d").astype(int)
        dates["jour"] = dates["date"].dt.day
        dates["mois"] = dates["date"].dt.month
        dates["trimestre"] = dates["date"].dt.quarter
        dates["annee"] = dates["date"].dt.year
        _nouveaux(conn, "dim_date", "id_temps", dates, ["id_temps"])

        # 3) Relire les identifiants
        dp = pd.read_sql("SELECT id_produit, produit, categorie FROM dim_produit", conn)\
               .drop_duplicates(["produit", "categorie"])
        dc = pd.read_sql("SELECT id_client, client FROM dim_client", conn)\
               .drop_duplicates("client")
        dagt = pd.read_sql(
            "SELECT id_agent, agent AS commercial FROM dim_agent WHERE id_agence = %(i)s",
            conn, params={"i": int(id_agence)}).drop_duplicates("commercial")

        v = ventes.copy()
        v["id_temps"] = v["date"].dt.strftime("%Y%m%d").astype(int)
        v["id_agence"] = int(id_agence)
        v = (v.merge(dp, on=["produit", "categorie"])
              .merge(dc, on="client")
              .merge(dagt, on="commercial"))
        fait = v[["id_temps", "id_agence", "id_agent", "id_client", "id_produit",
                  "quantite", "prix_unitaire", "montant"]]

        # 4) Faits
        if remplacer:
            conn.execute(text("DELETE FROM fait_vente WHERE id_agence = :i"), {"i": int(id_agence)})
        fait.to_sql("fait_vente", conn, if_exists="append", index=False)

    return {"agence": agence, "id_agence": int(id_agence), "creee": creee,
            "lignes_chargees": len(fait)}
