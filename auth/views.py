
from django.shortcuts import render, redirect

from auth.forms import UserCreationForm, SignupForm


def signup(request):
    # if this is a POST request we need to process the form data
    if request.method == 'POST':
        # create a form instance and populate it with data from the request:
        form = SignupForm(request.POST)
        # check whether it's valid:
        if form.is_valid():
            form.save()
            return redirect('signup-thanks')

    # if a GET (or any other method) we'll create a blank form
    else:
        form = SignupForm()

    return render(request, 'accounts/signup.html', {'form': form})