from django.db import models
from django.contrib.auth.models import AbstractUser
from PIL import Image
from io import BytesIO
from DProject.settings import AUTH_USER_MODEL
from django.core.files import File


# Create your models here.

class User(AbstractUser):
    first_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=11, blank=True)


class Category(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField()

    class Meta:
        ordering = ('name',)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return f'/{self.slug}/'


class Meal(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(default='')
    price = models.IntegerField()
    protein = models.IntegerField(default=0)  # белки
    fats = models.IntegerField(default=0)  # жиры
    carbs = models.IntegerField(default=0)  # углеводы
    description = models.TextField(null=True, blank=True)
    available_inventory = models.PositiveIntegerField(default=0)
    image = models.ImageField(blank=True, null=True)
    thumbnail = models.ImageField(upload_to='uploads/', blank=True, null=True)
    category = models.ForeignKey(Category, related_name='meals', on_delete=models.CASCADE)

    # if needs category name add to_field='name', db_column='category',

    class Meta:
        ordering = ('name',)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return f'/{self.category.slug}/{self.slug}/'

    def get_image(self):
        if self.image:
            # ss = HttpRequest.get_full_path
            return f'http://127.0.0.1:8000' + self.image.url
        return ''

    def get_thumbnail(self):
        if self.thumbnail:
            return 'http://127.0.0.1:8000' + self.thumbnail.url
        else:
            if self.image:
                self.thumbnail = self.make_thumbnail(self.image)
                self.save()

                return 'http://127.0.0.1:8000' + self.thumbnail.url
            else:
                return ''

    def make_thumbnail(self, image, size=(200, 200)):
        img = Image.open(image)
        img.convert('RGB')
        img.thumbnail(size, Image.ANTIALIAS)

        thumb_io = BytesIO()
        img.save(thumb_io, 'PNG', quality=85)

        thumbnail = File(thumb_io, name=image.name)

        return thumbnail


class Cart(models.Model):
    """A model that contains data for a shopping cart."""
    customer = models.OneToOneField(
        AUTH_USER_MODEL,
        related_name='cart',
        on_delete=models.CASCADE
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class CartItem(models.Model):
    """A model that contains data for an item in the shopping cart."""
    cart = models.ForeignKey(
        Cart,
        related_name='items',
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    meal = models.ForeignKey(
        Meal,
        related_name='items',
        on_delete=models.CASCADE
    )
    quantity = models.PositiveIntegerField(default=1, null=True, blank=True)

    def __unicode__(self):
        return '%s: %s' % (self.meal.name, self.quantity)


class Order(models.Model):
    """
    An Order is the more permanent counterpart of the shopping cart. It represents
    the frozen the state of the cart on the moment of a purchase. In other words,
    an order is a customer purchase.
    """
    customer = models.ForeignKey(
        AUTH_USER_MODEL,
        related_name='orders',
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    total = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class OrderItem(models.Model):
    """A model that contains data for an item in an order."""
    order = models.ForeignKey(
        Order,
        related_name='order_items',
        on_delete=models.CASCADE
    )
    meal = models.ForeignKey(
        Meal,
        related_name='order_items',
        on_delete=models.CASCADE
    )
    quantity = models.PositiveIntegerField(null=True, blank=True)

    def __unicode__(self):
        return '%s: %s' % (self.meal.name, self.quantity)
