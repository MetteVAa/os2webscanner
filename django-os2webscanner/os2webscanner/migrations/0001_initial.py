# -*- coding: utf-8 -*-


from django.db import migrations, models
import recurrence.fields
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ConversionQueueItem',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('file', models.CharField(max_length=4096, verbose_name=b'Fil')),
                ('type', models.CharField(max_length=256, verbose_name=b'Type')),
                ('page_no', models.IntegerField(null=True, verbose_name=b'Side')),
                ('status', models.CharField(default=b'NEW', max_length=10, verbose_name=b'Status', choices=[(b'NEW', b'Ny'), (b'PROCESSING', b'I gang'), (b'FAILED', b'Fejlet')])),
                ('process_id', models.IntegerField(null=True, verbose_name=b'Proces id', blank=True)),
                ('process_start_time', models.DateTimeField(null=True, verbose_name=b'Proces starttidspunkt', blank=True)),
            ],
        ),
        migrations.CreateModel(
            name='Domain',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('url', models.CharField(max_length=2048, verbose_name=b'Url')),
                ('validation_status', models.IntegerField(default=0, verbose_name=b'Valideringsstatus', choices=[(0, b'Ugyldig'), (1, b'Gyldig')])),
                ('validation_method', models.IntegerField(default=0, verbose_name=b'Valideringsmetode', choices=[(0, b'robots.txt'), (1, b'webscan.html'), (2, b'Meta-felt')])),
                ('exclusion_rules', models.TextField(default=b'', verbose_name=b'Ekskluderingsregler', blank=True)),
                ('sitemap', models.FileField(upload_to=b'sitemaps', verbose_name=b'Sitemap Fil', blank=True)),
                ('sitemap_url', models.CharField(default=b'', max_length=2048, verbose_name=b'Sitemap Url', blank=True)),
                ('download_sitemap', models.BooleanField(default=True, verbose_name=b'Hent Sitemap fra serveren')),
            ],
        ),
        migrations.CreateModel(
            name='Group',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(unique=True, max_length=256, verbose_name=b'Navn')),
                ('contact_email', models.CharField(max_length=256, verbose_name=b'Email')),
                ('contact_phone', models.CharField(max_length=256, verbose_name=b'Telefon')),
            ],
            options={
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='Match',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('matched_data', models.CharField(max_length=1024, verbose_name=b'Data match')),
                ('matched_rule', models.CharField(max_length=256, verbose_name=b'Regel match')),
                ('sensitivity', models.IntegerField(default=2, verbose_name=b'F\xc3\xb8lsomhed', choices=[(0, 'Gr\xf8n'), (1, 'Gul'), (2, 'R\xf8d')])),
                ('match_context', models.CharField(max_length=1152, verbose_name=b'Kontekst')),
                ('page_no', models.IntegerField(null=True, verbose_name=b'Side')),
            ],
        ),
        migrations.CreateModel(
            name='Md5Sum',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('md5', models.CharField(max_length=32)),
                ('is_cpr_scan', models.BooleanField()),
                ('is_check_mod11', models.BooleanField()),
                ('is_ignore_irrelevant', models.BooleanField()),
            ],
        ),
        migrations.CreateModel(
            name='Organization',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(unique=True, max_length=256, verbose_name=b'Navn')),
                ('contact_email', models.CharField(max_length=256, verbose_name=b'Email')),
                ('contact_phone', models.CharField(max_length=256, verbose_name=b'Telefon')),
                ('do_use_groups', models.BooleanField(default=False, editable=False)),
                ('name_whitelist', models.TextField(default=b'', verbose_name=b'Godkendte navne', blank=True)),
                ('name_blacklist', models.TextField(default=b'', verbose_name=b'Sortlistede navne', blank=True)),
                ('address_whitelist', models.TextField(default=b'', verbose_name=b'Godkendte adresser', blank=True)),
                ('address_blacklist', models.TextField(default=b'', verbose_name=b'Sortlistede adresser', blank=True)),
            ],
        ),
        migrations.CreateModel(
            name='ReferrerUrl',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('url', models.CharField(max_length=2048, verbose_name=b'Url')),
            ],
        ),
        migrations.CreateModel(
            name='RegexRule',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(unique=True, max_length=256, verbose_name=b'Navn')),
                ('match_string', models.CharField(max_length=1024, verbose_name=b'Udtryk')),
                ('description', models.TextField(verbose_name=b'Beskrivelse')),
                ('sensitivity', models.IntegerField(default=2, verbose_name=b'F\xc3\xb8lsomhed', choices=[(0, 'Gr\xf8n'), (1, 'Gul'), (2, 'R\xf8d')])),
                ('group', models.ForeignKey(verbose_name=b'Gruppe', blank=True, to='os2webscanner.Group', null=True)),
                ('organization', models.ForeignKey(verbose_name=b'Organisation', to='os2webscanner.Organization')),
            ],
        ),
        migrations.CreateModel(
            name='Scan',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('start_time', models.DateTimeField(null=True, verbose_name=b'Starttidspunkt', blank=True)),
                ('end_time', models.DateTimeField(null=True, verbose_name=b'Sluttidspunkt', blank=True)),
                ('is_visible', models.BooleanField(default=True)),
                ('whitelisted_names', models.TextField(default=b'', max_length=4096, verbose_name=b'Godkendte navne', blank=True)),
                ('blacklisted_names', models.TextField(default=b'', max_length=4096, verbose_name=b'Sortlistede navne', blank=True)),
                ('whitelisted_addresses', models.TextField(default=b'', max_length=4096, verbose_name=b'Godkendte adresser', blank=True)),
                ('blacklisted_addresses', models.TextField(default=b'', max_length=4096, verbose_name=b'Sortlistede adresser', blank=True)),
                ('do_cpr_scan', models.BooleanField(default=True, verbose_name=b'CPR')),
                ('do_name_scan', models.BooleanField(default=False, verbose_name=b'Navn')),
                ('do_address_scan', models.BooleanField(default=False, verbose_name=b'Adresse')),
                ('do_ocr', models.BooleanField(default=False, verbose_name=b'Scan billeder')),
                ('do_cpr_modulus11', models.BooleanField(default=True, verbose_name=b'Check modulus-11')),
                ('do_cpr_ignore_irrelevant', models.BooleanField(default=True, verbose_name=b'Ignorer irrelevante f\xc3\xb8dselsdatoer')),
                ('do_link_check', models.BooleanField(default=False, verbose_name=b'Check links')),
                ('do_external_link_check', models.BooleanField(default=False, verbose_name=b'Eksterne links')),
                ('do_last_modified_check', models.BooleanField(default=True, verbose_name=b'Check Last-Modified')),
                ('do_last_modified_check_head_request', models.BooleanField(default=True, verbose_name=b'Brug HEAD request')),
                ('do_collect_cookies', models.BooleanField(default=False, verbose_name=b'Saml cookies')),
                ('columns', models.CommaSeparatedIntegerField(max_length=128, null=True, blank=True)),
                ('output_spreadsheet_file', models.BooleanField(default=False)),
                ('do_cpr_replace', models.BooleanField(default=False)),
                ('cpr_replace_text', models.CharField(max_length=2048, null=True, blank=True)),
                ('do_name_replace', models.BooleanField(default=False)),
                ('name_replace_text', models.CharField(max_length=2048, null=True, blank=True)),
                ('do_address_replace', models.BooleanField(default=False)),
                ('address_replace_text', models.CharField(max_length=2048, null=True, blank=True)),
                ('status', models.CharField(default=b'NEW', max_length=10, choices=[(b'NEW', b'Ny'), (b'STARTED', b'I gang'), (b'DONE', b'OK'), (b'FAILED', b'Fejlet')])),
                ('pause_non_ocr_conversions', models.BooleanField(default=False, verbose_name=b'Pause non-OCR conversions')),
                ('reason', models.CharField(default=b'', max_length=1024, verbose_name=b'\xc3\x85rsag', blank=True)),
                ('pid', models.IntegerField(null=True, verbose_name=b'Pid', blank=True)),
                ('domains', models.ManyToManyField(to='os2webscanner.Domain', verbose_name=b'Dom\xc3\xa6ner')),
            ],
        ),
        migrations.CreateModel(
            name='Scanner',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(unique=True, max_length=256, verbose_name=b'Navn')),
                ('schedule', recurrence.fields.RecurrenceField(max_length=1024, verbose_name=b'Planlagt afvikling')),
                ('do_cpr_scan', models.BooleanField(default=True, verbose_name=b'CPR')),
                ('do_name_scan', models.BooleanField(default=False, verbose_name=b'Navn')),
                ('do_address_scan', models.BooleanField(default=False, verbose_name=b'Adresse')),
                ('do_ocr', models.BooleanField(default=False, verbose_name=b'Scan billeder')),
                ('do_cpr_modulus11', models.BooleanField(default=True, verbose_name=b'Check modulus-11')),
                ('do_cpr_ignore_irrelevant', models.BooleanField(default=True, verbose_name=b'Ignorer irrelevante f\xc3\xb8dselsdatoer')),
                ('do_link_check', models.BooleanField(default=False, verbose_name=b'Check links')),
                ('do_external_link_check', models.BooleanField(default=False, verbose_name=b'Eksterne links')),
                ('do_last_modified_check', models.BooleanField(default=True, verbose_name=b'Check Last-Modified')),
                ('do_last_modified_check_head_request', models.BooleanField(default=True, verbose_name=b'Brug HEAD request')),
                ('do_collect_cookies', models.BooleanField(default=False, verbose_name=b'Saml cookies')),
                ('columns', models.CommaSeparatedIntegerField(max_length=128, null=True, blank=True)),
                ('output_spreadsheet_file', models.BooleanField(default=False)),
                ('do_cpr_replace', models.BooleanField(default=False)),
                ('cpr_replace_text', models.CharField(max_length=2048, null=True, blank=True)),
                ('do_name_replace', models.BooleanField(default=False)),
                ('name_replace_text', models.CharField(max_length=2048, null=True, blank=True)),
                ('do_address_replace', models.BooleanField(default=False)),
                ('address_replace_text', models.CharField(max_length=2048, null=True, blank=True)),
                ('encoded_process_urls', models.CharField(max_length=262144, null=True, blank=True)),
                ('do_run_synchronously', models.BooleanField(default=False)),
                ('is_visible', models.BooleanField(default=True)),
                ('domains', models.ManyToManyField(related_name='scanners', verbose_name=b'Dom\xc3\xa6ner', to='os2webscanner.Domain')),
                ('group', models.ForeignKey(verbose_name=b'Gruppe', blank=True, to='os2webscanner.Group', null=True)),
                ('organization', models.ForeignKey(verbose_name=b'Organisation', to='os2webscanner.Organization')),
            ],
            options={
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='Summary',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(unique=True, max_length=256, verbose_name=b'Navn')),
                ('description', models.TextField(null=True, verbose_name=b'Beskrivelse', blank=True)),
                ('schedule', recurrence.fields.RecurrenceField(max_length=1024, verbose_name=b'Planlagt afvikling')),
                ('last_run', models.DateTimeField(null=True, verbose_name=b'Sidste k\xc3\xb8rsel', blank=True)),
                ('do_email_recipients', models.BooleanField(default=False, verbose_name=b'Udsend mails')),
                ('group', models.ForeignKey(verbose_name=b'Gruppe', blank=True, to='os2webscanner.Group', null=True)),
                ('organization', models.ForeignKey(verbose_name=b'Organisation', to='os2webscanner.Organization')),
            ],
            options={
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='Url',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('url', models.CharField(max_length=2048, verbose_name=b'Url')),
                ('mime_type', models.CharField(max_length=256, verbose_name=b'Mime-type')),
                ('status_code', models.IntegerField(null=True, verbose_name=b'Status code', blank=True)),
                ('status_message', models.CharField(max_length=256, null=True, verbose_name=b'Status Message', blank=True)),
                ('referrers', models.ManyToManyField(related_name='linked_urls', verbose_name=b'Referrers', to='os2webscanner.ReferrerUrl')),
                ('scan', models.ForeignKey(related_name='urls', verbose_name=b'Scan', to='os2webscanner.Scan')),
            ],
        ),
        migrations.CreateModel(
            name='UrlLastModified',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('url', models.CharField(max_length=2048, verbose_name=b'Url')),
                ('last_modified', models.DateTimeField(null=True, verbose_name=b'Last-modified', blank=True)),
                ('links', models.ManyToManyField(to='os2webscanner.UrlLastModified', verbose_name=b'Links')),
                ('scanner', models.ForeignKey(verbose_name=b'Scanner', to='os2webscanner.Scanner')),
            ],
        ),
        migrations.CreateModel(
            name='UserProfile',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('is_group_admin', models.BooleanField(default=False)),
                ('is_upload_only', models.BooleanField(default=False)),
                ('organization', models.ForeignKey(verbose_name=b'Organisation', to='os2webscanner.Organization')),
                ('user', models.OneToOneField(related_name='profile', verbose_name=b'Bruger', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddField(
            model_name='summary',
            name='recipients',
            field=models.ManyToManyField(to='os2webscanner.UserProfile', verbose_name=b'Modtagere', blank=True),
        ),
        migrations.AddField(
            model_name='summary',
            name='scanners',
            field=models.ManyToManyField(to='os2webscanner.Scanner', verbose_name=b'Scannere', blank=True),
        ),
        migrations.AddField(
            model_name='scanner',
            name='recipients',
            field=models.ManyToManyField(to='os2webscanner.UserProfile', verbose_name=b'Modtagere', blank=True),
        ),
        migrations.AddField(
            model_name='scanner',
            name='regex_rules',
            field=models.ManyToManyField(to='os2webscanner.RegexRule', verbose_name=b'Regex regler', blank=True),
        ),
        migrations.AddField(
            model_name='scan',
            name='recipients',
            field=models.ManyToManyField(to='os2webscanner.UserProfile', blank=True),
        ),
        migrations.AddField(
            model_name='scan',
            name='regex_rules',
            field=models.ManyToManyField(to='os2webscanner.RegexRule', verbose_name=b'Regex regler', blank=True),
        ),
        migrations.AddField(
            model_name='scan',
            name='scanner',
            field=models.ForeignKey(related_name='scans', verbose_name=b'Scanner', to='os2webscanner.Scanner'),
        ),
        migrations.AddField(
            model_name='referrerurl',
            name='scan',
            field=models.ForeignKey(verbose_name=b'Scan', to='os2webscanner.Scan'),
        ),
        migrations.AddField(
            model_name='md5sum',
            name='organization',
            field=models.ForeignKey(verbose_name=b'Organisation', to='os2webscanner.Organization'),
        ),
        migrations.AddField(
            model_name='match',
            name='scan',
            field=models.ForeignKey(related_name='matches', verbose_name=b'Scan', to='os2webscanner.Scan'),
        ),
        migrations.AddField(
            model_name='match',
            name='url',
            field=models.ForeignKey(verbose_name=b'Url', to='os2webscanner.Url'),
        ),
        migrations.AddField(
            model_name='group',
            name='organization',
            field=models.ForeignKey(related_name='groups', verbose_name=b'Organisation', to='os2webscanner.Organization'),
        ),
        migrations.AddField(
            model_name='group',
            name='user_profiles',
            field=models.ManyToManyField(related_name='groups', verbose_name=b'Brugere', to='os2webscanner.UserProfile', blank=True),
        ),
        migrations.AddField(
            model_name='domain',
            name='group',
            field=models.ForeignKey(related_name='domains', verbose_name=b'Gruppe', blank=True, to='os2webscanner.Group', null=True),
        ),
        migrations.AddField(
            model_name='domain',
            name='organization',
            field=models.ForeignKey(related_name='domains', verbose_name=b'Organisation', to='os2webscanner.Organization'),
        ),
        migrations.AddField(
            model_name='conversionqueueitem',
            name='url',
            field=models.ForeignKey(verbose_name=b'Url', to='os2webscanner.Url'),
        ),
        migrations.AlterUniqueTogether(
            name='md5sum',
            unique_together=set([('md5', 'is_cpr_scan', 'is_check_mod11', 'is_ignore_irrelevant', 'organization')]),
        ),
    ]
