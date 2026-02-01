from django.contrib import admin
from .models import FarmerProfile, Post, Comment, PostVote, Conversation, ConversationMessage


@admin.register(FarmerProfile)
class FarmerProfileAdmin(admin.ModelAdmin):
	list_display = ("full_name", "user", "state", "preferred_language", "created_at")
	search_fields = ("full_name", "user__username", "user__email", "state")


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
	list_display = ("id", "user", "created_at")
	list_filter = ("created_at",)
	search_fields = ("user__username", "content")


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
	list_display = ("id", "post", "user", "created_at")
	list_filter = ("created_at",)
	search_fields = ("user__username", "text")


@admin.register(PostVote)
class PostVoteAdmin(admin.ModelAdmin):
	list_display = ("id", "post", "user", "value", "created_at")
	list_filter = ("value", "created_at")
	search_fields = ("user__username",)


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
	list_display = ("id", "user", "title", "updated_at")
	search_fields = ("title", "user__username")


@admin.register(ConversationMessage)
class ConversationMessageAdmin(admin.ModelAdmin):
	list_display = ("id", "conversation", "role", "created_at")
	list_filter = ("role", "created_at")
	search_fields = ("text",)
