# Generated by Django 3.0 on 2020-01-05 11:04

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('jwt_auth', '0002_auto_20191229_1425'),
    ]

    operations = [
        migrations.CreateModel(
            name='ConsumerRule',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('type', models.CharField(choices=[('ip', 'IP Address'), ('http_access_control_origin', 'HTTP Access-Control-Origin')], max_length=32)),
                ('value', models.CharField(max_length=255)),
                ('action', models.CharField(choices=[('allow', 'Allow'), ('deny', 'Deny')], max_length=6)),
            ],
        ),
        migrations.RenameField(
            model_name='consumer',
            old_name='ip_rules_active',
            new_name='rules_active',
        ),
        migrations.DeleteModel(
            name='ConsumerIPRule',
        ),
        migrations.AddField(
            model_name='consumerrule',
            name='consumer',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='rules', to='jwt_auth.Consumer'),
        ),
    ]
