from django.http import JsonResponse
from graphene_django.views import GraphQLView
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication

# GraphQLView qui identifie l'utilisateur avec Authorization: Bearer <token>.
class JWTGraphQLView(GraphQLView):
    def dispatch(self, request, *args, **kwargs):
        try:
            result = JWTAuthentication().authenticate(request)
        except AuthenticationFailed:
            return JsonResponse(
                {"errors": [{"message": "Token invalide ou expiré."}]},
                status=401,
            )
        if result is not None:
            request.user, _ = result
        return super().dispatch(request, *args, **kwargs)