from abc import ABC

from rest_framework import serializers
from .models import *
from django.contrib.auth import authenticate


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'phone', 'password']
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user



class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(
        label="Username",
        write_only=True
    )
    password = serializers.CharField(
        label="Password",
        # This will be used when the DRF browsable API is enabled
        style={'input_type': 'password'},
        trim_whitespace=False,
        write_only=True
    )

    def validate(self, attrs):
        # Take username and password from request
        username = attrs.get('username')
        password = attrs.get('password')

        if username and password:
            # Try to authenticate the user using Django auth framework.
            user = authenticate(request=self.context.get('request'),
                                username=username, password=password)
            if not user:
                # If we don't have a regular user, raise a ValidationError
                msg = 'Неправильный логин или пароль'
                raise serializers.ValidationError(msg, code='authorization')
        else:
            msg = 'Заполните оба поля'
            raise serializers.ValidationError(msg, code='authorization')
        # We have a valid user, put it in the serializer's validated_data.
        # It will be used in the view.
        attrs['user'] = user
        return attrs


class MealSerializer(serializers.ModelSerializer):
    class Meta:
        model = Meal
        fields = (
            'id',  # productId
            'name',
            'get_absolute_url',
            'description',
            'price',
            'protein',
            'fats',
            'carbs',
            'available_inventory',
            'get_image',
            'get_thumbnail'
        )


class CategorySerializer(serializers.ModelSerializer):
    meals = MealSerializer(many=True)

    class Meta:
        model = Category
        fields = (
            'id', 'name', 'get_absolute_url', 'meals',
        )


class CartSerializer(serializers.ModelSerializer):
    """Serializer for the Cart model."""

    customer = UserSerializer(read_only=True)
    # used to represent the target of the relationship using its __unicode__ method
    items = serializers.StringRelatedField(many=True)

    class Meta:
        model = Cart
        fields = (
            'id', 'customer', 'created_at', 'updated_at', 'items'
        )


class CartItemSerializer(serializers.ModelSerializer):
    """Serializer for the CartItem model."""

    cart = CartSerializer(read_only=True)
    meal = MealSerializer(read_only=True)

    class Meta:
        model = CartItem
        fields = (
            'id', 'cart', 'meal', 'quantity'
        )


class OrderSerializer(serializers.ModelSerializer):
    """Serializer for the Order model."""

    customer = UserSerializer(read_only=True)
    # used to represent the target of the relationship using its __unicode__ method
    order_items = serializers.StringRelatedField(many=True, required=False)

    class Meta:
        model = Order
        fields = (
            'id', 'customer', 'total', 'created_at', 'updated_at', 'order_items'
        )

    def create(self, validated_data):  #
        order = Order.objects.create(**validated_data)
        return order


class OrderItemSerializer(serializers.ModelSerializer):
    """Serializer for the OrderItem model."""

    order = OrderSerializer(read_only=True)
    meal = MealSerializer(read_only=True)

    class Meta:
        model = OrderItem
        fields = (
            'id', 'order', 'meal', 'quantity'
        )
