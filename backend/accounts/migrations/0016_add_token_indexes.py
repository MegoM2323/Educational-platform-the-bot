from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0015_fix_parent_fk_cascade_action'),
        ('authtoken', '0002_auto_20160226_1747'),
    ]

    operations = [
        migrations.RunSQL(
            'CREATE INDEX IF NOT EXISTS authtoken_token_user_id_idx ON authtoken_token(user_id);',
            'DROP INDEX IF EXISTS authtoken_token_user_id_idx;',
        ),
        migrations.RunSQL(
            'CREATE INDEX IF NOT EXISTS authtoken_token_key_idx ON authtoken_token(key);',
            'DROP INDEX IF EXISTS authtoken_token_key_idx;',
        ),
    ]
