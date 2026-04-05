"""
Move AuthUser from the 'core' app to 'users'.

Uses SeparateDatabaseAndState so Django's migration state reflects the new
app label without touching the actual database (the auth_user table stays
exactly as it is).
"""

import django.contrib.auth.models
import django.core.validators
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        # Only auth is needed — no DB ops so no ordering dep on core migrations.
        # core.0005 depends on both core.0004 and users.0001 to enforce ordering.
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    # Tell Django's state that AuthUser now belongs to 'users'.
    # No database_operations — the table already exists.
    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.CreateModel(
                    name='AuthUser',
                    fields=[
                        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('first_name', models.CharField(
                            blank=True,
                            max_length=150,
                            validators=[
                                django.core.validators.RegexValidator(
                                    message="First name can only contain letters, hyphens, apostrophes, and spaces.",
                                    regex="^[a-zA-ZÀ-ÿ'\\- ]+$",
                                ),
                                django.core.validators.MinLengthValidator(2, message='First name must be at least 2 characters long.'),
                            ],
                        )),
                        ('last_name', models.CharField(
                            blank=True,
                            max_length=150,
                            validators=[
                                django.core.validators.RegexValidator(
                                    message="Last name can only contain letters, hyphens, apostrophes, and spaces.",
                                    regex="^[a-zA-ZÀ-ÿ'\\- ]+$",
                                ),
                                django.core.validators.MinLengthValidator(2, message='Last name must be at least 2 characters long.'),
                            ],
                        )),
                        ('username', models.CharField(
                            max_length=150,
                            unique=True,
                            validators=[
                                django.core.validators.RegexValidator(
                                    message='Username can only contain letters, numbers, dots, underscores, and hyphens.',
                                    regex='^[a-zA-Z0-9._-]+$',
                                ),
                                django.core.validators.MinLengthValidator(3, message='Username must be at least 3 characters long.'),
                            ],
                        )),
                        ('full_name', models.CharField(
                            blank=True,
                            max_length=255,
                            validators=[
                                django.core.validators.RegexValidator(
                                    message='Full name can only contain letters and spaces.',
                                    regex='^[a-zA-ZÀ-ÿ ]+$',
                                ),
                                django.core.validators.MinLengthValidator(2, message='Full name must be at least 2 characters long.'),
                                django.core.validators.MaxLengthValidator(255),
                            ],
                        )),
                        ('email', models.EmailField(
                            max_length=254,
                            unique=True,
                            validators=[
                                django.core.validators.RegexValidator(
                                    message='Enter a valid email address.',
                                    regex='^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$',
                                ),
                            ],
                        )),
                        ('email_verified', models.BooleanField(default=False, help_text="Indicates whether the user's email has been verified.")),
                        ('password', models.CharField(
                            help_text='Hashed password stored in the database.',
                            max_length=128,
                            validators=[
                                django.core.validators.MinLengthValidator(8, message='Password hash must be at least 8 characters (this should be set via Django settings).'),
                            ],
                        )),
                        ('is_superuser', models.BooleanField(default=False, help_text='Designates that this user has all permissions without explicitly assigning them.')),
                        ('is_staff', models.BooleanField(default=False, help_text='Designates whether the user can log into the admin site.')),
                        ('is_active', models.BooleanField(default=True, help_text='Designates whether this user account should be treated as active. Unselect this instead of deleting accounts.')),
                        ('date_joined', models.DateTimeField(default=django.utils.timezone.now, help_text='Date and time when the user account was created.')),
                        ('last_login', models.DateTimeField(blank=True, help_text="Date and time of the user's last successful login.", null=True)),
                        ('profile_picture', models.URLField(
                            blank=True,
                            help_text="URL to the user's profile picture (typically from Google OAuth or uploaded to CDN).",
                            max_length=1024,
                            null=True,
                            validators=[
                                django.core.validators.RegexValidator(
                                    message='Profile picture URL must use HTTPS protocol for security.',
                                    regex='^https://.*',
                                ),
                            ],
                        )),
                        ('groups', models.ManyToManyField(
                            blank=True,
                            help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.',
                            related_name='user_set',
                            related_query_name='user',
                            to='auth.group',
                            verbose_name='groups',
                        )),
                        ('user_permissions', models.ManyToManyField(
                            blank=True,
                            help_text='Specific permissions for this user.',
                            related_name='user_set',
                            related_query_name='user',
                            to='auth.permission',
                            verbose_name='user permissions',
                        )),
                    ],
                    options={
                        'verbose_name': 'User',
                        'verbose_name_plural': 'Users',
                        'db_table': 'auth_user',
                        'ordering': ['-date_joined'],
                        'managed': True,
                    },
                    managers=[
                        ('objects', django.contrib.auth.models.UserManager()),
                    ],
                ),
            ],
            database_operations=[],
        ),
    ]
