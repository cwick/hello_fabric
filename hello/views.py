from django.http import HttpResponse

def home(request):
    return HttpResponse("It Worked, part II")
