from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

User = get_user_model()

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, style={"input_type": "password"})
    class Meta:
        model = User
        fields = ["id", "username", "email", "password"]
        
        def validate_password(self, value):
            validate_password(value)
            return value
        
        def create(self, validated_data):
            return User.objects.create_user(**validated_data) # hache le mot de passe
    
class MeSerializer(serializers.ModelSerializer):
    class Meta:
        model = User