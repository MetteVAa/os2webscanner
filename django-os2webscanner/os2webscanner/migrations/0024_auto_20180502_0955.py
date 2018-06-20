# -*- coding: utf-8 -*-
# Generated by Django 1.11.9 on 2018-05-02 07:55
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('os2webscanner', '0023_auto_20180501_1133'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='filescan',
            name='domains',
        ),
        migrations.RemoveField(
            model_name='webscan',
            name='domains',
        ),
        migrations.AddField(
            model_name='scan',
            name='domains',
            field=models.ManyToManyField(to='os2webscanner.Domain', verbose_name='Domæner'),
        ),
    ]
