from django.db import models

class Building(models.Model):
    code = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    def __str__(self):
        return f"{self.name} ({self.code})"

class Route(models.Model):
    room_code = models.CharField(max_length=10, unique=True)
    building = models.ForeignKey(Building, on_delete=models.CASCADE)
    floor = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.room_code

class Step(models.Model):
    route = models.ForeignKey(Route, on_delete=models.CASCADE, related_name='steps')
    step_number = models.IntegerField()
    description = models.TextField()
    image = models.ImageField(upload_to='route_steps/', blank=True, null=True)

    class Meta:
        ordering = ['step_number']

    def __str__(self):
        return f"Шаг {self.step_number} для {self.route.room_code}"
