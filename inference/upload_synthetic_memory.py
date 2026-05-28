"""
upload_synthetic_memory.py
==========================
Uploads synthetic episodic memory + passage stubs to MongoDB Atlas.
Run this once to seed your database so you can test the inference
pipeline before your teammate's offline training is done.

Usage:
    pip install pymongo
    export MONGO_URI="mongodb+srv://<user>:<pass>@<cluster>.mongodb.net/"
    python upload_synthetic_memory.py

What it creates:
    Database : hotpotqa_rag
    Collections:
        episodic_memory  — 30 verified multi-hop reasoning chains
                           (schema matches teammate's offline output)
        passages         — 34 Wikipedia passage stubs
                           (corpus for BM25 retrieval)

    Indexes:
        episodic_memory.failure_type  (for quality gate filter)
        episodic_memory.quality_score (for quality gate filter)
        passages.title                (for lookup)

    Atlas Vector Search index:
        See instructions printed at end — must be created in Atlas UI
        (cannot be created via pymongo, only via Atlas API or UI)
"""

import os
import json
import math
import random
import hashlib
from datetime import datetime, timedelta
from pymongo import MongoClient, ASCENDING
from dotenv import load_dotenv

load_dotenv()   
# ── connection ────────────────────────────────────────────────────────────────
MONGO_URI = os.getenv(
    "MONGO_URI",
    "mongodb+srv://<user>:<password>@<cluster>.mongodb.net/"
)
DB_NAME = "hotpotqa_rag"

# ── data ──────────────────────────────────────────────────────────────────────

TEMPLATES = [
    ("Which tennis player won the tournament held in the city where the Eiffel Tower is located in 2023?",
     "Paris", "Eiffel Tower → Paris → Roland Garros → Novak Djokovic",
     "Roland Garros", "Eiffel Tower", "Novak Djokovic",
     ["Paris", "France", "tennis", "tournament"],
     "Geography landmark → city → venue → event winner chain"),

    ("What is the capital of the country where the Amazon River primarily flows?",
     "Brazil", "Amazon River → Brazil → Brasília",
     "Amazon River", "Brazil", "Brasília",
     ["Brazil", "South America", "river", "capital"],
     "Natural landmark → country → capital city chain"),

    ("Who founded the company that makes the iPhone?",
     "Apple Inc.", "iPhone → Apple Inc. → Steve Jobs",
     "iPhone", "Apple Inc.", "Steve Jobs",
     ["Apple", "technology", "smartphone", "Silicon Valley"],
     "Product → company → founder chain resolves cleanly"),

    ("In which city was the painter who created Starry Night born?",
     "Vincent van Gogh", "Starry Night → Vincent van Gogh → Zundert",
     "Starry Night", "Vincent van Gogh", "Zundert",
     ["painting", "Netherlands", "Post-Impressionism", "art"],
     "Artwork → artist → birthplace two-hop chain"),

    ("What language is spoken in the country that won the 2018 FIFA World Cup?",
     "France", "2018 FIFA World Cup → France → French",
     "2018 FIFA World Cup", "France", "French",
     ["football", "World Cup", "France", "Europe"],
     "Sports event → winner country → language chain"),

    ("Who wrote the novel that was adapted into the film directed by Francis Ford Coppola in 1972?",
     "The Godfather", "1972 Coppola film → The Godfather → Mario Puzo",
     "The Godfather (film)", "Mario Puzo", "Mario Puzo",
     ["film", "novel", "adaptation", "crime", "Coppola"],
     "Film → source novel → original author chain"),

    ("What is the currency of the country where the Sagrada Família is located?",
     "Spain", "Sagrada Família → Spain → Euro",
     "Sagrada Família", "Spain", "Euro",
     ["architecture", "Barcelona", "Spain", "Europe", "currency"],
     "Landmark → country → national currency two-hop"),

    ("Which university did the 44th president of the United States attend for law school?",
     "Barack Obama", "44th US president → Barack Obama → Harvard Law School",
     "Barack Obama", "Harvard Law School", "Harvard Law School",
     ["president", "United States", "law", "education"],
     "Ordinal position → person → institution educational chain"),

    ("What is the name of the river that flows through the city where Shakespeare was born?",
     "Stratford-upon-Avon", "Shakespeare → Stratford-upon-Avon → River Avon",
     "William Shakespeare", "Stratford-upon-Avon", "River Avon",
     ["Shakespeare", "England", "birthplace", "river"],
     "Person → birthplace → geographical feature chain"),

    ("Who directed the movie starring the actor who played Iron Man?",
     "Robert Downey Jr.", "Iron Man actor → Robert Downey Jr. → Jon Favreau",
     "Iron Man (film)", "Robert Downey Jr.", "Jon Favreau",
     ["Marvel", "superhero", "film", "actor", "director"],
     "Character → actor → film director chain"),

    ("What is the official language of the country that borders both France and Germany?",
     "Luxembourg", "France+Germany border → Luxembourg → Luxembourgish",
     "Luxembourg", "Languages of Luxembourg", "Luxembourgish",
     ["Europe", "border", "language", "small country"],
     "Geographic constraint → country → language chain"),

    ("Which element was discovered by the scientist who also discovered polonium?",
     "Marie Curie", "Polonium discoverer → Marie Curie → Radium",
     "Marie Curie", "Radium", "Radium",
     ["chemistry", "Nobel Prize", "radioactivity", "element"],
     "Scientific discovery → scientist → co-discovery chain"),

    ("In what year was the company founded that created the search engine with the largest market share?",
     "Google", "Largest search engine → Google → 1998",
     "Google", "History of Google", "1998",
     ["search engine", "technology", "internet", "company"],
     "Market position → company identity → founding year chain"),

    ("What is the capital of the country that shares a border with North Korea to the south?",
     "South Korea", "North Korea southern border → South Korea → Seoul",
     "South Korea", "Seoul", "Seoul",
     ["Korea", "Asia", "geopolitics", "capital", "border"],
     "Geopolitical relation → country → capital city"),

    ("Who was the first person to walk on the moon and what mission were they on?",
     "Neil Armstrong", "First moon walk → Neil Armstrong → Apollo 11",
     "Neil Armstrong", "Apollo 11", "Apollo 11",
     ["NASA", "space", "moon landing", "astronaut"],
     "Historical first → person → associated mission chain"),

    ("What version control system was created by the man who also created Linux?",
     "Linus Torvalds", "Linux creator → Linus Torvalds → Git",
     "Linus Torvalds", "Git", "Git",
     ["software", "open source", "programming", "kernel"],
     "Software product → creator → other creations chain"),

    ("In which country is the headquarters of the company that manufactures the Bugatti Chiron?",
     "Bugatti", "Bugatti Chiron → Bugatti → France",
     "Bugatti Chiron", "Bugatti", "France",
     ["automobile", "luxury", "car manufacturer", "Europe"],
     "Product → manufacturer → headquarters country chain"),

    ("What is the name of the ocean that borders the western coast of the United States?",
     "United States west coast", "US western coast → Pacific Ocean",
     "United States", "Pacific Ocean", "Pacific Ocean",
     ["geography", "ocean", "United States", "coast"],
     "Country + directional constraint → bordering ocean"),

    ("Who wrote the play that features the character Hamlet?",
     "Hamlet", "Hamlet character → Hamlet play → William Shakespeare",
     "Hamlet", "William Shakespeare", "William Shakespeare",
     ["literature", "theatre", "character", "play", "England"],
     "Fictional character → work → author chain"),

    ("What is the tallest mountain on the continent where the Nile River is located?",
     "Africa", "Nile River → Africa → Mount Kilimanjaro",
     "Nile", "Mount Kilimanjaro", "Mount Kilimanjaro",
     ["geography", "Africa", "mountain", "river", "continent"],
     "River → continent → tallest geographical feature chain"),

    ("Who invented the telephone and what country was he born in?",
     "Alexander Graham Bell",
     "Telephone → Alexander Graham Bell → Scotland",
     "Telephone", "Alexander Graham Bell", "Scotland",
     ["invention", "communication", "technology", "Scotland"],
     "Invention → inventor → birthplace chain"),

    ("What is the official language of the country that has the largest population in South America?",
     "Brazil", "Largest South American population → Brazil → Portuguese",
     "Brazil", "Portuguese language", "Portuguese",
     ["South America", "population", "language", "Brazil"],
     "Superlative constraint → country → official language"),

    ("Which actress won the Academy Award for the film where she played a Holocaust survivor?",
     "Sophie's Choice",
     "Holocaust survivor film → Sophie's Choice → Meryl Streep",
     "Sophie's Choice", "Meryl Streep", "Meryl Streep",
     ["film", "Holocaust", "Academy Award", "actress"],
     "Film theme → specific film → lead actress award chain"),

    ("What is the name of the sea that separates Europe from Africa at the Strait of Gibraltar?",
     "Strait of Gibraltar",
     "Strait of Gibraltar → Mediterranean Sea",
     "Strait of Gibraltar", "Mediterranean Sea", "Mediterranean Sea",
     ["geography", "strait", "Europe", "Africa", "sea"],
     "Geographical connector → body of water identification"),

    ("Who is the author of the Harry Potter series and where was she born?",
     "J.K. Rowling", "Harry Potter → J.K. Rowling → Yate, England",
     "Harry Potter", "J.K. Rowling", "Yate, Gloucestershire, England",
     ["literature", "fantasy", "author", "England", "series"],
     "Book series → author → birthplace chain"),

    ("What currency does the country use that is home to the Colosseum?",
     "Italy", "Colosseum → Italy → Euro",
     "Colosseum", "Italy", "Euro",
     ["architecture", "Italy", "Rome", "currency", "Europe"],
     "Monument → host country → national currency"),

    ("Which scientist developed the theory of relativity and won the Nobel Prize in Physics?",
     "Albert Einstein",
     "Theory of relativity → Albert Einstein → Nobel Prize 1921",
     "Theory of relativity", "Albert Einstein", "Albert Einstein",
     ["physics", "Nobel Prize", "relativity", "science"],
     "Scientific theory → developer → associated prize chain"),

    ("What is the name of the river that runs through the city where the Louvre museum is located?",
     "Paris", "Louvre → Paris → Seine River",
     "Louvre", "Seine", "Seine",
     ["museum", "Paris", "France", "river", "art"],
     "Landmark → city → river through that city chain"),

    ("Who composed the Four Seasons and what nationality was he?",
     "Antonio Vivaldi",
     "Four Seasons → Antonio Vivaldi → Italian",
     "The Four Seasons (Vivaldi)", "Antonio Vivaldi", "Italian",
     ["music", "classical", "composer", "baroque", "Italy"],
     "Musical work → composer → nationality chain"),

    ("What is the name of the mountain range that forms the natural border between France and Spain?",
     "France-Spain border",
     "France-Spain border → Pyrenees",
     "France", "Spain", "Pyrenees",
     ["geography", "mountain", "border", "Europe", "France", "Spain"],
     "Country pair + border constraint → mountain range chain"),
]

PASSAGES = [
    ("Roland Garros", ["Paris", "France", "tennis", "clay court", "French Open"],
     "Roland Garros is a tennis complex in Paris, France, home to the French Open Grand Slam tournament held annually on clay courts. The 2023 French Open Men's Singles was won by Novak Djokovic."),
    ("Eiffel Tower", ["Paris", "France", "landmark", "iron", "1889"],
     "The Eiffel Tower is a wrought-iron lattice tower on the Champ de Mars in Paris, France. It was constructed in 1889 and is the most visited paid monument in the world."),
    ("Amazon River", ["Brazil", "South America", "river", "rainforest", "longest"],
     "The Amazon River in South America is the largest river by discharge volume. It flows primarily through Brazil and discharges into the Atlantic Ocean near Marajó Island."),
    ("Brazil", ["South America", "country", "Portuguese", "Brasília", "football"],
     "Brazil is the largest country in South America. Its capital is Brasília. The official language is Portuguese. Brazil has the largest population in South America at over 215 million."),
    ("iPhone", ["Apple", "smartphone", "Steve Jobs", "technology", "iOS"],
     "The iPhone is a line of smartphones designed and marketed by Apple Inc. The first iPhone was introduced by Steve Jobs on January 9, 2007 at the Macworld Expo."),
    ("Apple Inc.", ["Steve Jobs", "Steve Wozniak", "technology", "Cupertino", "1976"],
     "Apple Inc. was co-founded on April 1, 1976 by Steve Jobs, Steve Wozniak, and Ronald Wayne. Headquartered in Cupertino, California. It is one of the world's most valuable companies."),
    ("Starry Night", ["Van Gogh", "Post-Impressionism", "painting", "1889", "MoMA"],
     "The Starry Night is an oil-on-canvas painting by Dutch Post-Impressionist painter Vincent van Gogh. Painted in June 1889, it depicts a swirling night sky over a village and is held at MoMA."),
    ("Vincent van Gogh", ["Netherlands", "painter", "Zundert", "Post-Impressionism"],
     "Vincent Willem van Gogh was a Dutch Post-Impressionist painter born on March 30, 1853 in Zundert, Netherlands. He created over 2000 artworks during his lifetime including The Starry Night."),
    ("2018 FIFA World Cup", ["France", "football", "Russia", "Deschamps", "trophy"],
     "The 2018 FIFA World Cup was held in Russia from June to July 2018. France won the tournament, defeating Croatia 4-2 in the final on July 15. It was France's second World Cup title."),
    ("France", ["Europe", "Paris", "French", "Republic", "Napoleon"],
     "France is a country in Western Europe. Its capital and largest city is Paris. The official language is French. France won the 2018 FIFA World Cup defeating Croatia in the final."),
    ("The Godfather (film)", ["Coppola", "1972", "Marlon Brando", "Paramount", "crime"],
     "The Godfather is a 1972 American crime film directed by Francis Ford Coppola. It is based on Mario Puzo's 1969 novel of the same name. The film stars Marlon Brando and Al Pacino."),
    ("Mario Puzo", ["novelist", "The Godfather", "Italian-American", "1920", "New York"],
     "Mario Puzo was an American author born on October 15, 1920 in New York City. He wrote The Godfather, published in 1969. Puzo co-wrote the screenplay for the 1972 film adaptation."),
    ("Sagrada Família", ["Barcelona", "Spain", "Gaudí", "cathedral", "architecture"],
     "The Sagrada Família is a large unfinished Roman Catholic minor basilica in Barcelona, Spain, designed by Catalan architect Antoni Gaudí. Spain is a member of the Eurozone and uses the Euro."),
    ("Barack Obama", ["44th president", "United States", "Harvard", "Illinois", "Democrat"],
     "Barack Obama served as the 44th president of the United States from 2009 to 2017. He attended Harvard Law School where he was the first African American president of the Harvard Law Review."),
    ("William Shakespeare", ["playwright", "Stratford-upon-Avon", "English", "Hamlet", "Globe Theatre"],
     "William Shakespeare was an English playwright and poet born in Stratford-upon-Avon, England in April 1564. The River Avon flows through Stratford-upon-Avon where he was born and buried."),
    ("Iron Man (film)", ["Marvel", "2008", "Robert Downey Jr.", "Jon Favreau", "superhero"],
     "Iron Man is a 2008 superhero film directed by Jon Favreau and starring Robert Downey Jr. as Tony Stark / Iron Man. It was the first film in the Marvel Cinematic Universe."),
    ("Luxembourg", ["Europe", "country", "Luxembourgish", "France", "Germany", "border"],
     "Luxembourg is a small landlocked country in Western Europe bordered by Belgium, France, and Germany. It has three official languages: Luxembourgish, French, and German."),
    ("Marie Curie", ["physicist", "chemist", "polonium", "radium", "Nobel Prize"],
     "Marie Curie was a Polish-French physicist and chemist. She discovered both polonium and radium. She was awarded two Nobel Prizes making her the only person to win Nobel Prizes in two sciences."),
    ("Google", ["search engine", "technology", "1998", "Larry Page", "Sergey Brin"],
     "Google LLC was founded in September 1998 by Larry Page and Sergey Brin while they were PhD students at Stanford University. Google has the largest search engine market share globally."),
    ("Neil Armstrong", ["astronaut", "Apollo 11", "moon", "NASA", "1969"],
     "Neil Armstrong was an American astronaut and aeronautical engineer. On July 20, 1969, he became the first person to walk on the Moon during the Apollo 11 mission."),
    ("Linus Torvalds", ["Linux", "software", "Finnish", "Git", "open source"],
     "Linus Torvalds is a Finnish-American software engineer who created the Linux kernel in 1991. In 2005 he also created Git, the distributed version control system used by millions of developers."),
    ("Bugatti Chiron", ["Bugatti", "supercar", "France", "luxury", "W16 engine"],
     "The Bugatti Chiron is a mid-engine two-seater sports car manufactured by Bugatti Automobiles S.A.S. Bugatti is headquartered in Molsheim, Alsace, in the Alsace region of France."),
    ("United States", ["North America", "country", "Washington D.C.", "English", "Pacific"],
     "The United States of America is a country in North America. Its western coast borders the Pacific Ocean. It has 50 states and a federal capital district Washington D.C."),
    ("Pacific Ocean", ["ocean", "largest", "Pacific Rim", "west coast", "Asia"],
     "The Pacific Ocean is the largest and deepest of Earth's oceanic divisions. It borders the western coast of North America including the United States."),
    ("Hamlet", ["Shakespeare", "play", "Denmark", "tragedy", "Ophelia"],
     "Hamlet is a tragedy written by William Shakespeare. It is believed to have been written between 1599 and 1601. The play follows Prince Hamlet of Denmark seeking revenge for his father's murder."),
    ("Mount Kilimanjaro", ["Africa", "Tanzania", "highest mountain", "Uhuru Peak", "5895m"],
     "Mount Kilimanjaro is a volcanic mountain in Tanzania, Africa. At 5,895 metres it is the highest mountain in Africa. The Nile River, the longest river in Africa, flows north from central Africa."),
    ("Telephone", ["Alexander Graham Bell", "invention", "1876", "communication", "patent"],
     "The telephone was invented by Alexander Graham Bell. Bell was born on March 3, 1847 in Edinburgh, Scotland. He was granted US Patent 174,465 for the telephone on March 7, 1876."),
    ("Sophie's Choice", ["film", "1982", "Meryl Streep", "Academy Award", "Holocaust"],
     "Sophie's Choice is a 1982 American drama film starring Meryl Streep as a Polish Holocaust survivor. Meryl Streep won the Academy Award for Best Actress for this role at the 55th Academy Awards."),
    ("Strait of Gibraltar", ["Europe", "Africa", "Atlantic", "Mediterranean", "Spain", "Morocco"],
     "The Strait of Gibraltar is a narrow waterway connecting the Atlantic Ocean to the Mediterranean Sea. It separates the Iberian Peninsula in Europe from Morocco in Africa."),
    ("J.K. Rowling", ["Harry Potter", "author", "British", "Yate", "fantasy"],
     "J.K. Rowling is a British author born on July 31, 1965 in Yate, Gloucestershire, England. She wrote the Harry Potter fantasy novel series, one of the best-selling book series in history."),
    ("Colosseum", ["Rome", "Italy", "amphitheatre", "ancient", "landmark"],
     "The Colosseum is an oval amphitheatre in the centre of Rome, Italy. Built between 70-80 AD, it is the largest ancient amphitheatre ever built. Italy is part of the Eurozone and uses the Euro."),
    ("Albert Einstein", ["physicist", "relativity", "Nobel Prize", "Germany", "1921"],
     "Albert Einstein was a German-born theoretical physicist who developed the theory of relativity. He was awarded the Nobel Prize in Physics in 1921 for his discovery of the law of the photoelectric effect."),
    ("Louvre", ["Paris", "France", "museum", "art", "Mona Lisa"],
     "The Louvre Museum is the world's most-visited art museum, located in Paris, France. The Seine river flows alongside it. It houses the Mona Lisa and the Venus de Milo among its 35,000 works."),
    ("Seine", ["Paris", "France", "river", "Île-de-France", "Notre-Dame"],
     "The Seine is a 775-kilometre long river that flows through Paris, France. Major Paris landmarks on its banks include the Louvre museum, Notre-Dame Cathedral, and the Eiffel Tower."),
]


def make_embedding(text: str, dim: int = 768) -> list:
    """Deterministic pseudo-embedding from text hash. Reproduces exactly."""
    h = hashlib.sha256(text.encode()).digest()
    rng = random.Random(int.from_bytes(h[:4], "big"))
    vec = [rng.gauss(0, 1) for _ in range(dim)]
    norm = math.sqrt(sum(x * x for x in vec))
    return [round(x / norm, 6) for x in vec]


def build_episodic_records() -> list:
    records = []
    base_ts = datetime(2026, 5, 1)
    random.seed(42)

    for idx, t in enumerate(TEMPLATES):
        (query, bridge, chain, p1_title, p2_title, answer,
         shared_ents, key_lesson) = t

        q_score = round(random.uniform(0.72, 0.97), 4)
        chosen  = random.choice(["A", "B"])

        records.append({
            "_id":             f"mem_{idx:04d}",
            "query":           query,
            "answer":          answer,
            "supporting_docs": [p1_title, p2_title],
            "bridge_entity":   bridge,
            "chain":           chain,
            "shared_entities": shared_ents,
            "quality_score":   q_score,
            "chosen_agent":    chosen,
            "agent_a": {
                "passage_id":        f"passage_{p1_title.lower().replace(' ', '_')[:30]}",
                "title":             p1_title,
                "confidence":        round(random.uniform(0.65, 0.90), 3),
                "shared_entities":   shared_ents[:3],
                "failure_diagnosis": (
                    f"Entity overlap with '{bridge}' identified in passage"
                ),
            },
            "agent_b": {
                "passage_id":    f"passage_{p1_title.lower().replace(' ', '_')[:30]}",
                "title":         p1_title,
                "bridge_entity": bridge,
                "chain":         chain,
                "chain_verified":True,
                "confidence":    round(random.uniform(0.70, 0.95), 3),
            },
            "failure_type":  "resolved",
            "key_lesson":    key_lesson,
            "embedding":     make_embedding(query, dim=768),
            "timestamp":     (base_ts + timedelta(hours=idx * 3)).isoformat() + "Z",
            "hop_count":     2,
            "verified":      True,
            "dataset":       "synthetic_hotpotqa_v1",
        })
    return records


def build_passage_records() -> list:
    return [
        {
            "_id":      f"passage_{title.lower().replace(' ', '_').replace('/', '_')[:40]}",
            "title":    title,
            "text":     text,
            "entities": entities,
            "source":   "synthetic_wikipedia_v1",
        }
        for title, entities, text in PASSAGES
    ]


# ── upload ────────────────────────────────────────────────────────────────────

def upload(mongo_uri: str = MONGO_URI):
    print(f"Connecting to MongoDB...")
    client = MongoClient(mongo_uri, serverSelectionTimeoutMS=10_000)

    # ping to verify connection
    client.admin.command("ping")
    print("Connected ✓")

    db = client[DB_NAME]

    # ── episodic_memory ───────────────────────────────────────────────────────
    mem_col = db["episodic_memory"]
    mem_col.drop()
    records = build_episodic_records()
    result  = mem_col.insert_many(records)
    print(f"episodic_memory : inserted {len(result.inserted_ids)} documents ✓")

    # standard indexes (filter at vector search time)
    mem_col.create_index([("failure_type",  ASCENDING)])
    mem_col.create_index([("quality_score", ASCENDING)])
    mem_col.create_index([("bridge_entity", ASCENDING)])
    mem_col.create_index([("verified",      ASCENDING)])
    print("episodic_memory : indexes created ✓")

    # ── passages ──────────────────────────────────────────────────────────────
    pass_col = db["passages"]
    pass_col.drop()
    passage_records = build_passage_records()
    result2         = pass_col.insert_many(passage_records)
    print(f"passages        : inserted {len(result2.inserted_ids)} documents ✓")
    pass_col.create_index([("title", ASCENDING)])
    print("passages        : indexes created ✓")

    # ── inference_results (empty, written by inference pipeline) ──────────────
    if "inference_results" not in db.list_collection_names():
        db.create_collection("inference_results")
        print("inference_results: collection created (empty, ready for writes) ✓")

    # ── instructions ──────────────────────────────────────────────────────────
    print("""
╔══════════════════════════════════════════════════════════════════╗
║  NEXT STEP — Create Atlas Vector Search Index (manual, 1 min)   ║
╠══════════════════════════════════════════════════════════════════╣
║  1. Go to Atlas UI → your cluster → Search & Vector Search       ║
║  2. Click "Create Search Index" → JSON editor                    ║
║  3. Select database: hotpotqa_rag                                ║
║     collection:      episodic_memory                             ║
║  4. Paste this JSON:                                             ║
╚══════════════════════════════════════════════════════════════════╝

{
  "fields": [
    {
      "type": "vector",
      "path": "embedding",
      "numDimensions": 768,
      "similarity": "cosine"
    },
    {
      "type": "filter",
      "path": "failure_type"
    },
    {
      "type": "filter",
      "path": "quality_score"
    }
  ]
}

Index name: episodic_embedding_index

After creating the index (takes ~2 min to build),
run verify_upload.py to confirm everything is working.
""")

    client.close()
    print("Upload complete.")


if __name__ == "__main__":
    uri = os.environ.get("MONGO_URI", "")
    if not uri or "<user>" in uri:
        print("ERROR: Set MONGO_URI environment variable first.")
        print("  export MONGO_URI='mongodb+srv://user:pass@cluster.mongodb.net/'")
        raise SystemExit(1)
    upload(uri)