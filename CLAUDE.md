# Règles du projet technical-rag-assistant

## Ce que c'est
RAG local et hors ligne sur des datasheets (ESP32 pour l'instant). Python 3.11, ChromaDB,
sentence-transformers, Ollama (llama3.2:3b, moondream). Code dans src/, mesures dans tests/ et docs/.

## Interdits
- Ne jamais lancer git commit ni git push : c'est l'utilisateur qui commite.
- Ne jamais modifier data/, ni les fichiers docs/benchmark_* et docs/retrieval_*.
- Ne jamais ajuster un seuil, un prompt, TOP_K ou USE_HYBRID pour faire passer une question du benchmark.
- Ne jamais modifier une question ou une réponse attendue de tests/benchmark_questions.json
  après avoir vu le résultat du système dessus.

## Méthode de mesure
- Toute modification qui change le comportement se mesure sur des questions NON encore vues
  (Q01 à Q22 sont "vues"). La règle de décision est écrite avant la mesure.
- Le LLM varie d'un lancement à l'autre (Q01, Q03, Q11 ont changé sans changement de code) :
  comparer question par question, jamais sur un seul pourcentage.
- Dans le README et les rapports : n'écrire que ce qui est mesuré. Signaler toute cause non vérifiée
  par "non vérifié".

## Règle de décision sur USE_HYBRID (écrite avant la mesure sur Q23 à Q27)
L'hybride devient le mode par défaut si, sur Q23 à Q27, il a au plus autant d'erreurs silencieuses
que les embeddings ET au moins autant de réponses correctes. Sinon il reste désactivé et on le documente.

## Façon de travailler
- Proposer un plan avant d'éditer, puis montrer le git diff à la fin.
- Lister ce qui a surpris dans le code existant.
- Expliquer simplement chaque changement : l'utilisateur est élève-ingénieur et doit pouvoir le défendre.
- Ne lancer le benchmark complet que sur demande explicite.