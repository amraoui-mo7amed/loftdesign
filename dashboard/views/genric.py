from django.http import JsonResponse, HttpResponseBadRequest
from django.views import View
from django.shortcuts import get_object_or_404

class BaseDeleteView(View):
    model = None  # must be defined in subclass

    def post(self, request, pk, *args, **kwargs):
        if not self.model:
            return HttpResponseBadRequest("No model defined")

        obj = get_object_or_404(self.model, pk=pk)
        obj.delete()
        return JsonResponse({"success": True, "message": "تم الحذف بنجاح"})
