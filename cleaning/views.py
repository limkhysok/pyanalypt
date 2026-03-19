

import os
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import CleaningOperation
from .serializers import CleaningOperationSerializer
from datasets.models import Dataset
from core.data_engine import load_data, generate_summary_stats
import pandas as pd


class CleaningOperationViewSet(viewsets.ModelViewSet):
    queryset = CleaningOperation.objects.all()
    serializer_class = CleaningOperationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = CleaningOperation.objects.filter(dataset__user=user)
        dataset_id = self.request.query_params.get("dataset")
        if dataset_id:
            qs = qs.filter(dataset_id=dataset_id)
        return qs


    @action(detail=True, methods=["post"])
    def revert(self, request, pk=None):
        """POST /cleaning/{id}/revert/ — revert a cleaning operation."""
        op = self.get_object()
        if op.status != "APPLIED":
            return Response({"detail": "Only applied operations can be reverted."}, status=status.HTTP_400_BAD_REQUEST)

        dataset = op.dataset
        # Try to revert by restoring from parent if available
        if dataset.parent:
            # Restore file from parent
            parent_file = dataset.parent.file.path
            current_file = dataset.file.path
            try:
                with open(parent_file, "rb") as src, open(current_file, "wb") as dst:
                    dst.write(src.read())
                op.status = "REVERTED"
                op.save(update_fields=["status"])
                dataset.is_cleaned = False
                dataset.save(update_fields=["is_cleaned"])
                return Response({"detail": "Dataset reverted to parent version."})
            except Exception as e:
                return Response({"detail": f"Failed to revert: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            return Response({"detail": "No parent dataset to revert to."}, status=status.HTTP_400_BAD_REQUEST)


    @action(detail=False, methods=["post"])
    def preview(self, request):
        """POST /cleaning/preview/ — preview the effect of a cleaning operation (not applied)."""
        dataset_id = request.data.get("dataset")
        operation_type = request.data.get("operation_type")
        column_name = request.data.get("column_name", "")
        parameters = request.data.get("parameters", {})
        if not dataset_id or not operation_type:
            return Response({"detail": "dataset and operation_type are required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            dataset = Dataset.objects.get(id=dataset_id)
            file_path = dataset.file.path
            df = load_data(file_path)
            df_preview = self.apply_cleaning_operation(df.copy(), operation_type, column_name, parameters)
            summary = generate_summary_stats(df_preview)
            # Return a sample and summary
            sample = df_preview.head(10).to_dict(orient="records")
            return Response({"summary": summary, "sample": sample})
        except Exception as e:
            return Response({"detail": f"Preview failed: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def apply_cleaning_operation(self, df, operation_type, column_name, parameters):
        # Basic implementations for demo; expand as needed
        if operation_type == "FILL_NA":
            value = parameters.get("value", 0)
            if column_name:
                df[column_name] = df[column_name].fillna(value)
            else:
                df = df.fillna(value)
        elif operation_type == "DROP_ROWS":
            condition = parameters.get("condition")
            if column_name and condition:
                df = df.query(f"{column_name}{condition}")
        elif operation_type == "DROP_DUPLICATES":
            df = df.drop_duplicates()
        elif operation_type == "CLIP_OUTLIERS":
            if column_name:
                lower = parameters.get("lower")
                upper = parameters.get("upper")
                if lower is not None:
                    df[column_name] = df[column_name].clip(lower=lower)
                if upper is not None:
                    df[column_name] = df[column_name].clip(upper=upper)
        elif operation_type == "REMOVE_OUTLIERS":
            if column_name:
                q1 = df[column_name].quantile(0.25)
                q3 = df[column_name].quantile(0.75)
                iqr = q3 - q1
                lower = q1 - 1.5 * iqr
                upper = q3 + 1.5 * iqr
                df = df[(df[column_name] >= lower) & (df[column_name] <= upper)]
        elif operation_type == "CAST_COLUMN":
            dtype = parameters.get("dtype", "str")
            if column_name:
                df[column_name] = df[column_name].astype(dtype)
        elif operation_type == "STANDARDIZE_FORMAT":
            # Example: lower case for string columns
            if column_name:
                df[column_name] = df[column_name].astype(str).str.lower()
        elif operation_type == "REPLACE_VALUES":
            if column_name and "to_replace" in parameters and "value" in parameters:
                df[column_name] = df[column_name].replace(parameters["to_replace"], parameters["value"])
        elif operation_type == "STRIP_WHITESPACE":
            if column_name:
                df[column_name] = df[column_name].astype(str).str.strip()
        elif operation_type == "FIX_ENCODING":
            # Not implemented: would require re-reading with correct encoding
            pass
        elif operation_type == "STANDARDIZE_CASE":
            if column_name:
                df[column_name] = df[column_name].astype(str).str.lower()
        elif operation_type == "RENAME_COLUMN":
            new_name = parameters.get("new_name")
            if column_name and new_name:
                df = df.rename(columns={column_name: new_name})
        return df
