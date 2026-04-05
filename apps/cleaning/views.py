

from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import CleaningOperation
from .serializers import CleaningOperationSerializer
from apps.datasets.models import Dataset
from apps.core.data_engine import load_data, generate_summary_stats

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
        operation_method = getattr(self, f"_clean_{operation_type.lower()}", self._clean_unsupported)
        return operation_method(df, column_name, parameters)

    def _clean_unsupported(self, df, column_name, parameters):
        return df

    def _clean_fill_na(self, df, column_name, parameters):
        value = parameters.get("value", 0)
        if column_name:
            df[column_name] = df[column_name].fillna(value)
        else:
            df = df.fillna(value)
        return df

    def _clean_drop_rows(self, df, column_name, parameters):
        condition = parameters.get("condition")
        if column_name and condition:
            df = df.query(f"{column_name}{condition}")
        return df

    def _clean_drop_duplicates(self, df, column_name, parameters):
        return df.drop_duplicates()

    def _clean_clip_outliers(self, df, column_name, parameters):
        if column_name:
            lower = parameters.get("lower")
            upper = parameters.get("upper")
            if lower is not None:
                df[column_name] = df[column_name].clip(lower=lower)
            if upper is not None:
                df[column_name] = df[column_name].clip(upper=upper)
        return df

    def _clean_remove_outliers(self, df, column_name, parameters):
        if column_name:
            q1 = df[column_name].quantile(0.25)
            q3 = df[column_name].quantile(0.75)
            iqr = q3 - q1
            lower = q1 - 1.5 * iqr
            upper = q3 + 1.5 * iqr
            df = df[(df[column_name] >= lower) & (df[column_name] <= upper)]
        return df

    def _clean_cast_column(self, df, column_name, parameters):
        dtype = parameters.get("dtype", "str")
        if column_name:
            df[column_name] = df[column_name].astype(dtype)
        return df

    def _clean_standardize_format(self, df, column_name, parameters):
        # Merged logic with standardize_case to resolve identical branch warnings
        return self._clean_standardize_case(df, column_name, parameters)

    def _clean_replace_values(self, df, column_name, parameters):
        if column_name and "to_replace" in parameters and "value" in parameters:
            df[column_name] = df[column_name].replace(parameters["to_replace"], parameters["value"])
        return df

    def _clean_strip_whitespace(self, df, column_name, parameters):
        if column_name:
            df[column_name] = df[column_name].astype(str).str.strip()
        return df

    def _clean_fix_encoding(self, df, column_name, parameters):
        return df

    def _clean_standardize_case(self, df, column_name, parameters):
        if column_name:
            df[column_name] = df[column_name].astype(str).str.lower()
        return df

    def _clean_rename_column(self, df, column_name, parameters):
        new_name = parameters.get("new_name")
        if column_name and new_name:
            df = df.rename(columns={column_name: new_name})
        return df
