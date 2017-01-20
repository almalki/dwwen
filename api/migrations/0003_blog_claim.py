# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'BlogClaim'
        db.create_table(u'api_blogclaim', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('blog', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['api.Blog'])),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.DwwenUser'])),
            ('is_verified', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('verification_key', self.gf('django.db.models.fields.CharField')(max_length=300)),
            ('expire_at', self.gf('django.db.models.fields.DateTimeField')()),
        ))
        db.send_create_signal(u'api', ['BlogClaim'])


    def backwards(self, orm):
        # Deleting model 'BlogClaim'
        db.delete_table(u'api_blogclaim')


    models = {
        u'api.blog': {
            'Meta': {'object_name': 'Blog'},
            'alive': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'blog_url': ('django.db.models.fields.URLField', [], {'unique': 'True', 'max_length': '2048'}),
            'categories': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['api.BlogCategory']", 'symmetrical': 'False'}),
            'country': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['cities_light.Country']", 'null': 'True', 'blank': 'True'}),
            'created_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '500'}),
            'followers': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'following'", 'symmetrical': 'False', 'through': u"orm['api.UserBlog']", 'to': u"orm['auth.DwwenUser']"}),
            'http_etag': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'}),
            'http_last_modified': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'blank': 'True'}),
            'last_update_date': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '60'}),
            'rss_url': ('django.db.models.fields.URLField', [], {'unique': 'True', 'max_length': '2048'}),
            'status': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'blogs'", 'blank': 'True', 'to': u"orm['auth.DwwenUser']"})
        },
        u'api.blogcategory': {
            'Meta': {'object_name': 'BlogCategory'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'api.blogclaim': {
            'Meta': {'object_name': 'BlogClaim'},
            'blog': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.Blog']"}),
            'expire_at': ('django.db.models.fields.DateTimeField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_verified': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.DwwenUser']"}),
            'verification_key': ('django.db.models.fields.CharField', [], {'max_length': '300'})
        },
        u'api.favoritepost': {
            'Meta': {'unique_together': "(('user', 'post'),)", 'object_name': 'FavoritePost'},
            'created_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'post': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'favorites'", 'to': u"orm['api.Post']"}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'favorites'", 'to': u"orm['auth.DwwenUser']"})
        },
        u'api.post': {
            'Meta': {'object_name': 'Post'},
            'alive': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'blog': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.Blog']"}),
            'content': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'created_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'favorited_by': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'favorited_posts'", 'symmetrical': 'False', 'through': u"orm['api.FavoritePost']", 'to': u"orm['auth.DwwenUser']"}),
            'full_content': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'max_length': '100'}),
            'last_update_date': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'liked_by': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'liked_posts'", 'symmetrical': 'False', 'through': u"orm['api.PostLike']", 'to': u"orm['auth.DwwenUser']"}),
            'link': ('django.db.models.fields.URLField', [], {'unique': 'True', 'max_length': '2048'}),
            'published_date': ('django.db.models.fields.DateTimeField', [], {}),
            'summary': ('django.db.models.fields.TextField', [], {}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        u'api.postlike': {
            'Meta': {'unique_together': "(('user', 'post'),)", 'object_name': 'PostLike'},
            'created_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'post': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'like'", 'to': u"orm['api.Post']"}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.DwwenUser']"})
        },
        u'api.posttag': {
            'Meta': {'object_name': 'PostTag'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'post': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'tags'", 'to': u"orm['api.Post']"}),
            'tag': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'api.userblog': {
            'Meta': {'unique_together': "(('user', 'blog'),)", 'object_name': 'UserBlog'},
            'blog': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.Blog']"}),
            'created_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.DwwenUser']"})
        },
        u'auth.dwwenuser': {
            'Meta': {'object_name': 'DwwenUser'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'unique': 'True', 'max_length': '75'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Group']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Permission']"}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '15'})
        },
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'cities_light.country': {
            'Meta': {'ordering': "['name']", 'object_name': 'Country'},
            'alternate_names': ('django.db.models.fields.TextField', [], {'default': "''", 'null': 'True', 'blank': 'True'}),
            'code2': ('django.db.models.fields.CharField', [], {'max_length': '2', 'unique': 'True', 'null': 'True', 'blank': 'True'}),
            'code3': ('django.db.models.fields.CharField', [], {'max_length': '3', 'unique': 'True', 'null': 'True', 'blank': 'True'}),
            'continent': ('django.db.models.fields.CharField', [], {'max_length': '2', 'db_index': 'True'}),
            'geoname_id': ('django.db.models.fields.IntegerField', [], {'unique': 'True', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '200'}),
            'name_ascii': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '200', 'blank': 'True'}),
            'slug': ('autoslug.fields.AutoSlugField', [], {'unique_with': '()', 'max_length': '50', 'populate_from': "'name_ascii'"}),
            'tld': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '5', 'blank': 'True'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        }
    }

    complete_apps = ['api']