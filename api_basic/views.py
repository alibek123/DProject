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
    """
    API endpoint that allows carts to be viewed or edited.
    """
    queryset = Cart.objects.all()
    serializer_class = CartSerializer

    @action(methods=['post', 'put'], detail=True)  # вместо detail_route
    def add_to_cart(self, request, pk=None):
        """Add an item to a user's cart.

        Adding to cart is disallowed if there is not enough inventory for the
        product available. If there is, the quantity is increased on an existing
        cart item or a new cart item is created with that quantity and added
        to the cart.

        Return the updated cart.

        """

        cart = self.get_object()
        try:
            meal = Meal.objects.get(
                pk=request.data["id"]
            )
            quantity = int(request.data["quantity"])
        except Exception as e:
            print(e)
            return Response({'status': 'fail'})

        # Disallow adding to cart if available inventory is not enough
        if meal.available_inventory <= 0 or meal.available_inventory - quantity < 0:
            print("Этого продукта не осталось")
            return Response({'status': 'fail'})

        existing_cart_item = CartItem.objects.filter(cart=cart, meal=meal).first()
        # before creating a new cart item check if it is in the cart already
        # and if yes increase the quantity of that item
        if existing_cart_item:
            existing_cart_item.quantity += quantity
            existing_cart_item.save()
        else:
            new_cart_item = CartItem(cart=cart, meal=meal, quantity=quantity)
            new_cart_item.save()

        # return the updated cart to indicate success
        serializer = CartSerializer(cart)
        return Response(serializer.data)

    @action(methods=['post', 'put'], detail=True)  # вместо detail_route
    def remove_from_cart(self, request, pk=None):
        """Remove an item from a user's cart.

        Customers can only remove items from the
        cart 1 at a time, so the quantity of the product to remove from the cart
        will always be 1. If the quantity of the product to remove from the cart
        is 1, delete the cart item. If the quantity is more than 1, decrease
        the quantity of the cart item, but leave it in the cart.

        Return the updated cart.

        """
        cart = self.get_object()
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

        # if removing an item where the quantity is 1, remove the cart item
        # completely otherwise decrease the quantity of the cart item
        if cart_item.quantity == 1:
            cart_item.delete()
        else:
            cart_item.quantity -= 1
            cart_item.save()

        # return the updated cart to indicate success
        serializer = CartSerializer(cart)
        return Response(serializer.data)


class CartItemViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows cart items to be viewed or edited.
    """
    queryset = CartItem.objects.all()
    serializer_class = CartItemSerializer


class OrderViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows orders to be viewed or created.
    """
    queryset = Order.objects.all()
    serializer_class = OrderSerializer

    def perform_create(self, serializer):
        """Add info and perform checks before saving an Order.

        Before creating an Order, there is a check on the customer's cart items.
        If the cart item quantity causes the product's available inventory to
        dip below zero, a validation error is raised.If there is enough inventory to support the order, an Order is created
        and cart items are used to make order items. After that the cart is
        cleared.

        NOTE: Cart items are not deleted. When the cart is cleared the cart items
        still exist but are disassociated from the cart. The cart is empty so
        that the user can add new things to it, but cart items are preserved as
        they could be helpful in drawing insights from customer behavior or making
        suggestions. For example, what they have put in their cart previously,
        what other similar products might she/he like, etc.

        Parameters
        ----------
        serializer: OrderSerialiazer
            Serialized representation of Order we are creating.

        """
        try:
            purchaser_id = self.request.data['customer']
            user = User.objects.get(pk=purchaser_id)
        except:
            raise serializers.ValidationError(
                'User was not found'
            )

        cart = user.cart

        for cart_item in cart.items.all():
            if cart_item.meal.available_inventory - cart_item.quantity < 0:
                raise serializers.ValidationError(
                    'We do not have enough inventory of ' + str(cart_item.meal.title) + \
                    'to complete your purchase. Sorry, we will restock soon'
                )

        # find the order total using the quantity of each cart item and the product's price
        total_aggregated_dict = cart.items.aggregate(
            total=Sum(F('quantity') * F('meal__price'), output_field=FloatField()))

        order_total = round(total_aggregated_dict['total'], 2)
        order = serializer.save(customer=user, total=order_total)

        order_items = []
        for cart_item in cart.items.all():
            order_items.append(OrderItem(order=order, meal=cart_item.meal, quantity=cart_item.quantity))
            # available_inventory should decrement by the appropriate amount
            cart_item.meal.available_inventory -= cart_item.quantity
            cart_item.meal.save()

        OrderItem.objects.bulk_create(order_items)
        # use clear instead of delete since it removes all objects from the
        # related object set. It doesnot delete the related objects it just
        # disassociates them, which is what we want in order to empty the cart
        # but keep cart items in the db for customer data analysis
        cart.items.clear()

    def create(self, request, *args, **kwargs):
        """Override the creation of Order objects.

        Parameters
        ----------
        request: dict
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    @action(detail=False, url_path="order_history/(?P<customer_id>[0-9])")
    def order_history(self, request, customer_id):
        """Return a list of a user's orders.

        Parameters
        ----------
        request: request

        """
        try:
            user = User.objects.get(id=customer_id)

        except:
            # no user was found, so order history cannot be retrieved.
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
