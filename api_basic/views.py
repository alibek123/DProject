from django.contrib.auth import login
from django.db.models import Sum, F, FloatField
from django.http import HttpResponse
from rest_framework import permissions, viewsets
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter
from rest_framework.generics import ListAPIView, CreateAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import *


# Create your views here.
class UserCreate(CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = (permissions.AllowAny,)


class LoginView(APIView):
    # This view should be accessible also for unauthenticated users.
    permission_classes = (permissions.AllowAny,)

    def post(self, request, format=None):
        serializer = LoginSerializer(data=self.request.data,
                                     context={'request': self.request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        login(request, user)
        return Response(serializer.data, status=status.HTTP_202_ACCEPTED)


class MealList(ListAPIView):
    serializer_class = MealSerializer
    queryset = Meal.objects.all()
    filter_backends = [SearchFilter]
    search_fields = ['name', 'price']


class MealAPIView(APIView):
    # filter_backends = [SearchFilter]
    # search_fields = ['name', 'price']

    def get(self, request):
        meals = Meal.objects.all()
        serializer = MealSerializer(meals, many=True)
        return Response(serializer.data)

    # def post(self, request):
    #     serializer = MealSerializer(data=request.data)
    #
    #     if serializer.is_valid():
    #         serializer.save()
    #         return Response(serializer.data, status=status.HTTP_201_CREATED)
    #     return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class MealDetails(APIView):

    def get_object(self, category_slug, meal_slug):
        try:
            return Meal.objects.filter(category__slug=category_slug).get(slug=meal_slug)
        except Meal.DoesNotExist:
            return HttpResponse(status=status.HTTP_404_NOT_FOUND)

    def get(self, request, category_slug, meal_slug):
        meal = self.get_object(category_slug, meal_slug)
        serializer = MealSerializer(meal)
        return Response(serializer.data)

    # def put(self, request, id):
    #     meal = self.get_object(id)
    #     serializer = MealSerializer(meal, data=request.data)
    #     if serializer.is_valid():
    #         serializer.save()
    #         return Response(serializer.data)
    #     return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    #
    # def delete(self, request, id):
    #     meal = self.get_object(id)
    #     meal.delete()
    #     return Response(status=status.HTTP_204_NO_CONTENT)


class CategoryDetail(APIView):
    def get_object(self, category_slug):
        try:
            return Category.objects.get(slug=category_slug)
        except Meal.DoesNotExist:
            return HttpResponse(status=status.HTTP_404_NOT_FOUND)

    def get(self, request, category_slug):
        category = self.get_object(category_slug)
        serializer = CategorySerializer(category)
        return Response(serializer.data)


class CartViewSet(viewsets.ModelViewSet):
    queryset = Cart.objects.all()
    serializer_class = CartSerializer

    def get_object(self):
        return Cart.objects.get_or_create(customer=self.request.user)

    def get_queryset(self):
        user_id = self.request.user.id
        queryset = self.queryset.filter(customer_id=user_id)
        return queryset

    @action(methods=['put'], detail=True)  # вместо detail_route
    def add_to_cart(self, request):  # ,pk=None

        Cart.objects.get_or_create(customer=self.request.user)
        cart = Cart.objects.get(customer=self.request.user)
        try:
            meal = Meal.objects.get(
                pk=request.data["id"]
            )
            quantity = int(request.data["quantity"])
        except Exception as e:
            print(e)
            return Response({'status': 'fail'})

        # Если кол-во товара в базе равно 0
        if meal.available_inventory <= 0 or meal.available_inventory - quantity < 0:
            print("Этого продукта не осталось")
            return Response({'status': 'fail'})

        existing_cart_item = CartItem.objects.filter(cart=cart, meal=meal).first()
        # До того как добавить в корзину новый товар убеждаемся что там нету этого товара
        if existing_cart_item:
            existing_cart_item.quantity += quantity
            existing_cart_item.save()
        else:
            new_cart_item = CartItem(cart=cart, meal=meal, quantity=quantity)
            new_cart_item.save()

        # возвращаем корзину
        serializer = CartSerializer(cart)
        return Response(serializer.data)

    @action(methods=['post', 'put'], detail=True)  # вместо detail_route
    def remove_from_cart(self, request, pk=None):
        # Удаляет по одному
        cart = self.get_object(self.request.user.id)
        try:
            meal = Meal.objects.get(
                pk=request.data.get('id')
            )
        except Exception as e:
            print(e)
            return Response({'status': 'fail'})

        try:
            cart_item = CartItem.objects.get(cart=cart, meal=meal)
        except Exception as e:
            print(e)
            return Response({'status': 'fail'})

        # если при удалении кол-во будет 1 то удаляем, если нет то кол-во -1
        if cart_item.quantity == 1:
            cart_item.delete()
        else:
            cart_item.quantity -= 1
            cart_item.save()

        # возвращаем корзину
        serializer = CartSerializer(cart)
        return Response(serializer.data)


class CartItemViewSet(viewsets.ModelViewSet):
    queryset = CartItem.objects.all()
    serializer_class = CartItemSerializer


class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all().order_by('-id')
    serializer_class = OrderSerializer

    def get_queryset(self):
        user_id = self.request.user.id
        queryset = self.queryset.filter(customer_id=user_id)
        return queryset

    def perform_create(self, serializer):

        # try:
        #     purchaser_id = self.request.user.id
        #     user = User.objects.get(pk=purchaser_id)
        # except:
        #     raise serializers.ValidationError(
        #         'User was not found'
        #     )
        user = User.objects.get(pk=self.request.user.id)
        cart = user.cart

        for cart_item in cart.items.all():
            if cart_item.meal.available_inventory - cart_item.quantity < 0:
                raise serializers.ValidationError(
                    'У нас не хватает ' + str(cart_item.meal.title) + \
                    'Скоро будет поступление'
                )

        # Сумма заказа
        total_aggregated_dict = cart.items.aggregate(
            total=Sum(F('quantity') * F('meal__price'), output_field=FloatField()))

        order_total = round(total_aggregated_dict['total'], 2)
        order = serializer.save(customer=self.request.user, total=order_total)

        order_items = []
        for cart_item in cart.items.all():
            order_items.append(OrderItem(order=order, meal=cart_item.meal, quantity=cart_item.quantity))
            # кол-во товаров отнимаются поскольку сделана покупка
            cart_item.meal.available_inventory -= cart_item.quantity
            cart_item.meal.save()

        OrderItem.objects.bulk_create(order_items)
        # Очищаем корзину
        cart.items.clear()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    @action(detail=False, url_path="order_history")
    def order_history(self, request):
        customer_id = self.request.user.id
        try:
            user = User.objects.get(id=customer_id)

        except:

            return Response({'status': 'fail'})

        orders = Order.objects.filter(customer=user)
        serializer = OrderSerializer(orders, many=True)

        return Response(serializer.data)


class OrderItemViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows order items to be viewed or edited.
    """
    queryset = OrderItem.objects.all()
    serializer_class = OrderItemSerializer
