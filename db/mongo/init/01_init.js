// Homepedia : initialisation MongoDB (exécuté au premier démarrage)
db = db.getSiblingDB("homepedia");

db.createCollection("avis", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["code_insee", "source", "texte", "date_collecte"],
      properties: {
        code_insee: { bsonType: "string", pattern: "^[0-9AB]{5}$" },
        source: { bsonType: "string" },
        url: { bsonType: "string" },
        texte: { bsonType: "string", minLength: 10 },
        texte_hash: { bsonType: "string" },
        notes: { bsonType: "object" },
        nlp: { bsonType: "object" }
      }
    }
  }
});
db.avis.createIndex({ code_insee: 1 });
db.avis.createIndex({ texte_hash: 1 }, { unique: true, sparse: true });
db.avis.createIndex({ "nlp.sentiment": 1, code_insee: 1 });
db.avis.createIndex({ texte: "text" }, { default_language: "french" });

db.createCollection("nlp_synthese_commune");
db.nlp_synthese_commune.createIndex({ code_insee: 1 }, { unique: true });

db.createCollection("raw_api");
db.raw_api.createIndex({ source: 1, code_insee: 1, collected_at: -1 });

db.createCollection("scrape_cache");
db.scrape_cache.createIndex({ url: 1 }, { unique: true });
