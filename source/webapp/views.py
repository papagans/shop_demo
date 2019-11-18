from django.http import HttpResponseRedirect
from django.shortcuts import reverse, redirect, get_object_or_404

from django.urls import reverse_lazy
from django.views import View
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView

from webapp.forms import BasketOrderCreateForm, ManualOrderForm, OrderProductForm
from webapp.models import Product, OrderProduct, Order
from django.contrib.auth.mixins import PermissionRequiredMixin, LoginRequiredMixin
from django.contrib import messages
from webapp.mixins import StatsMixin


class IndexView(StatsMixin, ListView):
    model = Product
    template_name = 'index.html'

    def get_queryset(self):
        return Product.objects.filter(in_order=True)


class ProductView(StatsMixin, DetailView):
    model = Product
    template_name = 'product/detail.html'


class ProductCreateView(PermissionRequiredMixin, StatsMixin, CreateView):
    model = Product
    template_name = 'product/create.html'
    fields = ('name', 'category', 'price', 'photo', 'in_order')
    permission_required = 'webapp.add_product'
    permission_denied_message = '403 Доступ запрещён!'

    def get_success_url(self):
        return reverse('webapp:product_detail', kwargs={'pk': self.object.pk})


class ProductUpdateView(PermissionRequiredMixin, StatsMixin, UpdateView):
    model = Product
    template_name = 'product/update.html'
    fields = ('name', 'category', 'price', 'photo', 'in_order')
    context_object_name = 'product'
    permission_required = 'webapp.change_product'
    permission_denied_message = '403 Доступ запрещён!'

    def get_success_url(self):
        return reverse('webapp:product_detail', kwargs={'pk': self.object.pk})


class ProductDeleteView(PermissionRequiredMixin, StatsMixin, DeleteView):
    model = Product
    template_name = 'product/delete.html'
    success_url = reverse_lazy('webapp:index')
    context_object_name = 'product'
    permission_required = 'webapp.delete_product'
    permission_denied_message = '403 Доступ запрещён!'

    def delete(self, request, *args, **kwargs):
        product = self.object = self.get_object()
        product.in_order = False
        product.save()
        return HttpResponseRedirect(self.get_success_url())


class BasketChangeView(StatsMixin, View):
    def get(self, request, *args, **kwargs):
        products = request.session.get('products', [])

        pk = request.GET.get('pk')
        action = request.GET.get('action')
        next_url = request.GET.get('next', reverse('webapp:index'))

        if action == 'add':
            product = get_object_or_404(Product, pk=pk)
            if product.in_order:
                products.append(pk)
        else:
            for product_pk in products:
                if product_pk == pk:
                    products.remove(product_pk)
                    break

        request.session['products'] = products
        request.session['products_count'] = len(products)

        return redirect(next_url)


class BasketView(StatsMixin, CreateView):
    model = Order
    form_class = BasketOrderCreateForm
    template_name = 'product/basket.html'
    success_url = reverse_lazy('webapp:index')

    def get_context_data(self, **kwargs):
        basket, basket_total = self._prepare_basket()
        kwargs['basket'] = basket
        kwargs['basket_total'] = basket_total
        return super().get_context_data(**kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        if self._basket_empty():
            form.add_error(None, 'В корзине отсутствуют товары!')
            return self.form_invalid(form)
        response = super().form_valid(form)
        self._save_order_products()
        self._clean_basket()
        messages.success(self.request, 'Заказ оформлен!')
        return response

    def _prepare_basket(self):
        totals = self._get_totals()
        basket = []
        basket_total = 0
        for pk, qty in totals.items():
            product = Product.objects.get(pk=int(pk))
            total = product.price * qty
            basket_total += total
            basket.append({'product': product, 'qty': qty, 'total': total})
        return basket, basket_total

    def _get_totals(self):
        products = self.request.session.get('products', [])
        totals = {}
        for product_pk in products:
            if product_pk not in totals:
                totals[product_pk] = 0
            totals[product_pk] += 1
        return totals

    def _basket_empty(self):
        products = self.request.session.get('products', [])
        return len(products) == 0

    def _save_order_products(self):
        totals = self._get_totals()
        for pk, qty in totals.items():
            OrderProduct.objects.create(product_id=pk, order=self.object, amount=qty)

    def _clean_basket(self):
        if 'products' in self.request.session:
            self.request.session.pop('products')
        if 'products_count' in self.request.session:
            self.request.session.pop('products_count')


class OrderListView(PermissionRequiredMixin, ListView):
    template_name = 'order/list.html'
    context_object_name = 'orders'
    permission_required = 'webapp.view_order'
    permission_denied_message = '403 Доступ запрещён!'

    def get_queryset(self):
        if self.request.user.has_perm('webapp:view_order'):
            return Order.objects.all().order_by('-created_at')
        return self.request.user.orders.all().order_by('-created_at')


class OrderDetailView(PermissionRequiredMixin,DetailView):
    template_name = 'order/detail.html'
    context_object_name = 'orders'
    model = Order
    permission_required = 'webapp.view_order'
    permission_denied_message = '403 Доступ запрещён!'

    def get_context_data(self, **kwargs):
        pk = self.kwargs.get('pk')
        context = super().get_context_data(**kwargs)
        order = self.object
        amount = OrderProduct.objects.all().filter(order=int(pk))
        amount_list = []
        total_price = 0
        for i in amount:
            total = i.product.price * int(i.amount)
            total_price += total
            amount_list.append({'product': i.product, 'price': i.product.price, 'qty': i.amount, 'total': total})
        context['order'] = order.products.all()
        context['amount_list'] = amount_list
        context['total_price'] = total_price
        return context

    def _get_totals(self):
        pk = self.kwargs.get('pk')
        tovar = Product.objects.all().filter(orders=int(pk))
        products = self.object
        totals = {}
        for product_pk in tovar:
            if product_pk not in totals:
                totals[product_pk] = 0
            totals[product_pk] += 1
        return totals

    def get_queryset(self):
        if self.request.user.has_perm('webapp:view_order'):
            return Order.objects.all()
        return self.request.user.orders.all()


class OrderCreateView(PermissionRequiredMixin, CreateView):
    model = Order
    template_name = 'order/order_create.html'
    context_object_name = 'order'
    form_class = ManualOrderForm
    permission_required = 'webapp.add_order'
    permission_denied_message = '403 Доступ запрещён!'

    def get_success_url(self):
        return reverse('webapp:order_detail', kwargs={'pk': self.object.pk})


class OrderUpdateView(PermissionRequiredMixin, UpdateView):
    template_name = 'order/order_update.html'
    model = Order
    context_object_name = 'order'
    form_class = ManualOrderForm
    permission_required = 'webapp.change_order'
    permission_denied_message = '403 Доступ запрещён!'

    def get_success_url(self):
        return reverse('webapp:order_detail', kwargs={'pk': self.object.pk})


class OrderDeliverView(PermissionRequiredMixin, View):
    model = Order
    permission_required = 'webapp.can_change_deliver'
    permission_denied_message = '403 Доступ запрещён!'

    def get(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        order = get_object_or_404(Order, id=pk)
        order.status = 'delivered'
        order.save()
        return redirect('webapp:order_detail', pk)

class OrderCancelView(PermissionRequiredMixin, View):
    model = Order
    permission_required = 'webapp.can_cancel'
    permission_denied_message = '403 Доступ запрещён!'

    def get(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        order = get_object_or_404(Order, id=pk)
        order.status = 'canceled'
        order.save()
        return redirect('webapp:order_detail', pk)


class OrderProductCreateView(PermissionRequiredMixin, CreateView):
    template_name = 'order/order_product_create.html'
    model = OrderProduct
    context_object_name = 'order'
    fields = ['product', 'amount']
    permission_required = 'webapp.add_order'
    permission_denied_message = '403 Доступ запрещён!'

    def form_valid(self, form):
        product = form.cleaned_data.pop('product')
        amount = form.cleaned_data.pop('amount')
        pk = self.kwargs.get('pk')
        order = get_object_or_404(Order, id=pk)
        OrderProduct.objects.create(order=order, product=product, amount=amount)

        return redirect('webapp:order_detail', pk)

    def get_context_data(self, **kwargs):
        pk = self.kwargs.get('pk')
        context = super().get_context_data(**kwargs)
        context['pk'] = pk
        print(pk)
        return context

    # def get_success_url(self):
    #     pk = self.kwargs.get('pk')
    #     return reverse('webapp:order_detail', kwargs={'pk': pk})


class OrderProductUpdateView(PermissionRequiredMixin, UpdateView):
    model = OrderProduct
    template_name = 'order/order_products_update.html'
    context_object_name = 'order'
    # form_class = OrderProductForm
    fields = ['product', 'amount']
    permission_required = 'webapp.change_order'
    permission_denied_message = '403 Доступ запрещён!'

    def form_valid(self, form):
        product = form.cleaned_data.pop('product')
        amount = form.cleaned_data.pop('amount')
        pk = self.kwargs.get('pk')
        order = get_object_or_404(Order, id=pk)
        OrderProduct.objects.create(order=order, product=product, amount=amount)

        return redirect('webapp:order_detail', pk)

    def get_success_url(self):
        return reverse('webapp:order_detail', kwargs={'pk': self.object.pk})


class OrderProductDeleteView(PermissionRequiredMixin, DeleteView):
    model = Order
    template_name = 'order/delete.html'
    success_url = reverse_lazy('webapp:order_list')
    context_object_name = 'order'
    permission_required = 'webapp.delete_product'
    permission_denied_message = '403 Доступ запрещён!'

    # def delete(self, request, *args, **kwargs):
    #     product = self.object = self.get_object()
    #     product.in_order = False
    #     product.save()
    #     return HttpResponseRedirect(self.get_success_url())