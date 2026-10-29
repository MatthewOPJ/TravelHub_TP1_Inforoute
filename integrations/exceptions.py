# erreurs utiles los des integrations d'API
# les noms s'expliquent d'eux même...

class ExternalServiceError(Exception):
    "Le service externe est inaccessible, trop lent ou renvoie une réponse invalide."

class LocationNotFound(Exception):
    "La destination n'a pas pu être identifiée par le service de géocodage."

class NoDataAvailable(Exception):
    "Le service répond, mais il n'a aucune donnée utile pour cette demande."