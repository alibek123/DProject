from django.urls import path, re_path, include
from rest_framework import routers
from .views import *

router = routers.DefaultRouter()
router.register(r'carts', CartViewSet)
router.register(r'cart_items', CartItemViewSet)
router.register(r'orders', OrderViewSet)
router.register(r'order_items', OrderItemViewSet)

make_order = OrderViewSet.as_view({
    'post': 'create'
})
add_to_cart = CartViewSet.as_view({
    'put': 'add_to_cart'
})

urlpatterns = [
    path('register/', UserCreate.as_view(), name='registration'),
    path('login/', LoginView.as_view()),
    path('meals/', MealAPIView.as_view()),
    path('orders/make_order/', make_order),
    path('carts/add_to_cart/', add_to_cart),
    # path('meals/search/', views.search),
    path('meals/<slug:category_slug>/<slug:meal_slug>/', MealDetails.as_view()),
    path('meals/<slug:category_slug>/', CategoryDetail.as_view()),
    re_path(r'^', include(router.urls)),

]
