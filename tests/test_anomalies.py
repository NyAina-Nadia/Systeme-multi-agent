def test_detecter_anomalies_colonnes():
    from ml.anomalies import detecter_anomalies
    df = detecter_anomalies()
    for col in ["agence", "produit", "quantite", "montant", "ratio", "score"]:
        assert col in df.columns
