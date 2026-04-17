from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from .models import Role, User
from .permissions import role_required


@login_required
def profile(request):
    return render(request, "accounts/profile.html", {"profile_user": request.user})


@role_required(Role.ADMIN)
def user_list(request):
    users = User.objects.all().order_by("role", "username")
    return render(request, "accounts/user_list.html", {"users": users})
