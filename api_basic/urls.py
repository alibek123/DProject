from django.urls import path, re_path, include
from rest_framework import routers
from .views import *

router = routers.DefaultRouter()
router.register(r'carts', CartViewSet)
router.register(r'cart_items', CartItemViewSet)
router.register(r'orders', OrderViewSet)
router.register(r'order_items', OrderItemViewSet)

urlpatterns = [
    path('register/', UserCreate.as_view(), name='registration'),
    path('login/', LoginView.as_view()),
    path('meals/', MealAPIView.as_view()),
    # path('meals/search/', views.search),
    path('meals/<slug:category_slug>/<slug:meal_slug>/', MealDetails.as_view()),
    path('meals/<slug:category_slug>/', CategoryDetail.as_view()),
    re_path(r'^', include(router.urls)),

]
