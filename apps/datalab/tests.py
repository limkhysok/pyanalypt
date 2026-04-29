import io
import pandas as pd
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APITestCase
from rest_framework import status
from apps.datasets.models import Dataset

User = get_user_model()


class DatalabMutationTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="password123")
        self.client.force_authenticate(user=self.user)
        
        # Create a sample DataFrame and save to CSV
        df = pd.DataFrame({
            "id": [1, 2, 3],
            "name": ["Alice", "Bob", None],
            "age": [25.0, 30.5, None],
            "status": ["active", "inactive", "active"]
        })
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False)
        csv_buffer.seek(0)
        
        file = SimpleUploadedFile("test_data.csv", csv_buffer.read().encode("utf-8"), content_type="text/csv")
        self.dataset = Dataset.objects.create(
            user=self.user,
            file=file,
            file_name="test_data.csv",
            file_format="csv"
        )
    
    def test_cast_columns(self):
        url = reverse("datalab-cast", args=[self.dataset.id])
        data = {"casts": {"age": "integer"}, "force": True}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.dataset.refresh_from_db()
        self.assertIn("age", self.dataset.column_casts)
        self.assertEqual(self.dataset.column_casts["age"], "integer")
        
    def test_fill_nulls(self):
        url = reverse("datalab-fill-nulls", args=[self.dataset.id])
        data = {"strategy": "constant", "columns": ["name"], "value": "Unknown"}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["cells_filled"], 1)
        
        # Check actual file modification
        preview_url = reverse("datalab-preview", args=[self.dataset.id])
        preview_res = self.client.get(preview_url)
        rows = preview_res.json()["rows"]
        self.assertEqual(rows[2]["name"], "Unknown")
        
    def test_drop_columns(self):
        url = reverse("datalab-drop-columns", args=[self.dataset.id])
        data = {"columns": ["status"]}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("status", response.json()["columns_dropped"])
        
        preview_url = reverse("datalab-preview", args=[self.dataset.id])
        preview_res = self.client.get(preview_url)
        columns = preview_res.json()["columns"]
        self.assertNotIn("status", columns)
        
    def test_filter_rows(self):
        url = reverse("datalab-filter-rows", args=[self.dataset.id])
        data = {"column": "age", "operator": "gt", "value": 26}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        preview_url = reverse("datalab-preview", args=[self.dataset.id])
        preview_res = self.client.get(preview_url)
        rows = preview_res.json()["rows"]
        # Only Bob matches (age 30.5)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["name"], "Bob")
