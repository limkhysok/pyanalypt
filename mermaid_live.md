erDiagram
    auth_user {
        int id PK
        string username
        string full_name
        string password
        boolean is_superuser
        string profile_picture
        string email
        boolean is_staff
        boolean is_active
        datetime last_login
        datetime date_joined
    }

    auth_group {
        int id PK
        string name
    }

    auth_permission {
        int id PK
        string name
        int content_type_id FK
        string codename
    }

    auth_user_groups {
        int id PK
        int user_id FK
        int group_id FK
    }

    auth_group_permissions {
        int id PK
        int group_id FK
        int permission_id FK
    }

    auth_user_user_permissions {
        int id PK
        int user_id FK
        int permission_id FK
    }

    django_content_type {
        int id PK
        string app_label
        string model
    }

    django_admin_log {
        int id PK
        datetime action_time
        string object_id
        string object_repr
        int action_flag
        text change_message
        int content_type_id FK
        int user_id FK
    }

    django_session {
        string session_key PK
        text session_data
        datetime expire_date
    }

    django_migrations {
        int id PK
        string app
        string name
        datetime applied
    }
    
    socialaccount_socialaccount {
        int id PK
        int user_id FK
        string provider
        string uid
        json extra_data
        datetime last_login
        datetime date_joined
    }

    %% AUTH RELATIONSHIPS
    auth_user ||--o{ auth_user_groups : "many-to-many"
    auth_user ||--o{ socialaccount_socialaccount : "linked_to"
    auth_group ||--o{ auth_user_groups : "many-to-many"

    auth_group ||--o{ auth_group_permissions : has
    auth_permission ||--o{ auth_group_permissions : assigned

    auth_user ||--o{ auth_user_user_permissions : has
    auth_permission ||--o{ auth_user_user_permissions : assigned

    auth_permission }o--|| django_content_type : references

    django_admin_log }o--|| auth_user : performed_by
    django_admin_log }o--|| django_content_type : relates_to
