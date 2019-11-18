from django.urls import path
from .views import IndexView, ProductView, ProductCreateView, BasketChangeView, BasketView, \
    ProductUpdateView, ProductDeleteView, OrderListView, OrderDetailView, OrderUpdateView, OrderProductUpdateView, \
    OrderCreateView, OrderProductCreateView, OrderDeliverView, OrderCancelView, OrderProductDeleteView

app_name = 'webapp'

urlpatterns = [
    path('', IndexView.as_view(), name='index'),
    path('products/<int:pk>/', ProductView.as_view(), name='product_detail'),
    path('products/create/', ProductCreateView.as_view(), name='product_create'),
    path('basket/change/', BasketChangeView.as_view(), name='basket_change'),
    path('basket/', BasketView.as_view(), name='basket'),
    path('products/<int:pk>/update/', ProductUpdateView.as_view(), name='product_update'),
    path('products/<int:pk>/delete/', ProductDeleteView.as_view(), name='product_delete'),
    path('orders/', OrderListView.as_view(), name='order_list'),
    path('orders/<int:pk>', OrderDetailView.as_view(), name='order_detail'),
    path('orders_update/<int:pk>', OrderUpdateView.as_view(), name='order_update'),
    path('orders/<int:pk>/products', OrderProductCreateView.as_view(), name='order_product_create'),
    path('orders_create/', OrderCreateView.as_view(), name='order_create'),
    path('orders_update/<int:pk>/products', OrderProductUpdateView.as_view(), name='order_product_update'),
    path('orders_delivered/<int:pk>', OrderDeliverView.as_view(), name='delivered'),
    path('orders_canceled/<int:pk>', OrderCancelView.as_view(), name='canceled'),
    path('orders_delete/<int:pk>', OrderProductDeleteView.as_view(), name='order_delete'),
]
