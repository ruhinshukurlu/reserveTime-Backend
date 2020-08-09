from django.shortcuts import render, redirect
from django.http import HttpResponse, HttpResponseRedirect
from django.views.generic import CreateView
from account.models import User
from account.forms import RestaurantRegisterForm, UserEditForm
from django.urls import reverse_lazy
from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import DetailView, UpdateView, FormView , DeleteView, ListView
from django.views.generic.edit import FormMixin
from restaurant.models import *
from restaurant.forms import *
from django.contrib import messages
import datetime


class RestaurantRegisterView(CreateView):
    model = User
    form_class = RestaurantRegisterForm
    template_name = 'register-restaurant.html'

    def get_context_data(self, **kwargs):
        kwargs['user_type'] = 'company'
        return super().get_context_data(**kwargs)

    def form_valid(self, form):
        user = form.save()
        login(self.request, user, backend='django.contrib.auth.backends.ModelBackend')
        return redirect('core:home')


class MenuView(CreateView):
    model = Menu
    form_class = MenuForm
    template_name = 'company-menus.html'
    success_url = reverse_lazy('restaurant:menu')
    
    def form_valid(self, form):
        form.instance.company = self.request.user
        form.save()
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["menus"] = Menu.objects.filter(company=self.request.user)
        context["menu_categories"] = MenuCategory.objects.all()
        
        return context


class MenuUpdateView(UpdateView):
    model = Menu
    template_name = "menu-detail.html"
    form_class = MenuForm

    def get_success_url(self):
        return reverse_lazy('restaurant:menu')


class MenuDeleteView(DeleteView):
    model = Menu
    template_name = "menu-detail.html"
    
    def get_success_url(self):
        return reverse_lazy('restaurant:menu')


class PhotoView(CreateView):
    model = Photo
    form_class = PhotoForm
    template_name = 'company-photos.html'
    success_url = reverse_lazy('restaurant:photo')

    def form_valid(self, form):
        form.instance.owner = self.request.user
        form.save()
        return super().form_valid(form)
    
    def form_invalid(self, form):
        messages.warning(self.request, 'Something went wrong!!')
        return super().form_invalid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["photos"] = Photo.objects.filter(owner=self.request.user)
        
        return context


class PhotoUpdateView(UpdateView):
    model = Photo
    template_name = "photo-detail.html"
    form_class = PhotoForm
    context_object_name = 'photo'

    def get_success_url(self):
        return reverse_lazy('restaurant:photo')
    

class PhotoDeleteView(DeleteView):
    model = Photo
    template_name = "photo-detail.html"
    
    def get_success_url(self):
        return reverse_lazy('restaurant:photo')


class CompanyInfosView(UpdateView):
    model = Company
    template_name = "company-infos.html"
    form_class = CompanyInfosForm
    context_object_name = 'company'
    
    def get_success_url(self, **kwargs):
        return reverse_lazy("restaurant:company-infos", kwargs={'pk': self.object.pk})


class CompanyTablesView(CreateView):
    model = Table
    template_name = 'company-tables.html'
    form_class = TableForm

    def get(self, request, *args, **kwargs):
        form = self.form_class()
        
        inside_tables = Table.objects.filter(table_place = 'inside', company=self.request.user).order_by('size')
        outside_tables = Table.objects.filter(table_place = 'outside', company=self.request.user).order_by('size')
        return render(request, self.template_name, {
                'form' : form, 
                'inside_tables' : inside_tables, 
                'outside_tables' : outside_tables
            })

    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST)

        if form.is_valid():
            amount = form.cleaned_data['amount']
            size = form.cleaned_data['size']
            place = form.cleaned_data['table_place']
             
            company_start_hour = self.request.user.company.work_hours_from
            company_finish_hour = self.request.user.company.work_hours_to
            free_times = []
            free_times.append(company_start_hour)
            while company_start_hour < company_finish_hour:
                company_start_hour = (datetime.datetime.combine(  
                        datetime.date(1, 1, 1),  
                        company_start_hour
                    ) + datetime.timedelta(minutes=30)).time()

                free_times.append(company_start_hour)
            
            free_times = free_times[:-1]
            
            reserve_start_date = datetime.date.today()
            reserve_finish_date = (datetime.date.today()+datetime.timedelta(days=30)).isoformat()
        
            reserve_dates = []
            for i in range(31):
                reserve_dates.append(reserve_start_date)
                reserve_start_date = (reserve_start_date+datetime.timedelta(days=1))

            for i in range(amount): 
                table = Table.objects.create(size = size, table_place = place, company = self.request.user)
                for free_time in free_times:
                    time = Time.objects.create(free_time = free_time, reserved = False)
                    table.times.add(time)
                for free_date in reserve_dates:
                    date = TableDate.objects.create(date=free_date)
                    table.dates.add(date)

            return HttpResponseRedirect(reverse_lazy('restaurant:company-tables', kwargs={'pk': self.request.user.pk}))

        return render(request,self.template_name, {'form' : form})


class TableDeleteView(DeleteView):
    model = Table
    template_name = "company-tables.html"
    
    def get_success_url(self):
        return reverse_lazy('restaurant:company-tables', kwargs={'pk': self.object.pk})  


class ResevedUserList(DetailView):
    model = Company
    template_name = 'company-users.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        company = Company.objects.filter(pk=self.kwargs.get('pk'))

        reservations = Reservation.objects.filter(company__in=company)

        reserved_user_list = []

        for reservation in reservations:
            if reservation.user not in reserved_user_list:
                reserved_user_list.append(reservation.user)

        context['reserved_users'] = reserved_user_list

        return context


class CompanyReservations(ListView):
    model = Reservation
    context_object_name = 'reservations'
    template_name='reservations-list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        company = Company.objects.filter(pk=self.kwargs.get('pk'))
        reservations = Reservation.objects.filter(user = self.request.user)
        print(reservations.first().user)
        context["party_size"] = Reservation.objects.filter(user = self.request.user)
        return context