from django.db import models
from django.contrib.auth.models import User


class FarmerProfile(models.Model):
	LANGUAGE_CHOICES = [
		('hi', 'Hindi'), ('en', 'English'), ('mr', 'Marathi'), ('ta', 'Tamil'),
		('te', 'Telugu'), ('bn', 'Bengali'), ('gu', 'Gujarati'), ('pa', 'Punjabi'),
		('ml', 'Malayalam'), ('kn', 'Kannada'),
	]

	STATE_CHOICES = [
		('AN', 'Andaman and Nicobar Islands'), ('AP', 'Andhra Pradesh'), ('AR', 'Arunachal Pradesh'),
		('AS', 'Assam'), ('BR', 'Bihar'), ('CH', 'Chandigarh'), ('CT', 'Chhattisgarh'),
		('DN', 'Dadra and Nagar Haveli and Daman and Diu'), ('DL', 'Delhi'), ('GA', 'Goa'),
		('GJ', 'Gujarat'), ('HR', 'Haryana'), ('HP', 'Himachal Pradesh'), ('JH', 'Jharkhand'),
		('JK', 'Jammu and Kashmir'), ('KA', 'Karnataka'), ('KL', 'Kerala'), ('LA', 'Ladakh'),
		('LD', 'Lakshadweep'), ('MP', 'Madhya Pradesh'), ('MH', 'Maharashtra'), ('MN', 'Manipur'),
		('ML', 'Meghalaya'), ('MZ', 'Mizoram'), ('NL', 'Nagaland'), ('OD', 'Odisha'), ('PB', 'Punjab'),
		('PY', 'Puducherry'), ('RJ', 'Rajasthan'), ('SK', 'Sikkim'), ('TN', 'Tamil Nadu'),
		('TS', 'Telangana'), ('TR', 'Tripura'), ('UP', 'Uttar Pradesh'), ('UK', 'Uttarakhand'),
		('WB', 'West Bengal')
	]

	FARMING_CHOICES = [
		('crop', 'Crop Farming'),
		('dairy', 'Dairy'),
		('poultry', 'Poultry'),
		('horticulture', 'Horticulture'),
		('mixed', 'Mixed/Others'),
	]

	user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='farmer_profile')
	full_name = models.CharField(max_length=120)
	phone = models.CharField(max_length=20, blank=True, null=True)
	state = models.CharField(max_length=2, choices=STATE_CHOICES)
	district_village = models.CharField(max_length=120, blank=True, null=True)
	farming_types = models.TextField(blank=True, null=True, help_text='Comma-separated values from FARMING_CHOICES')
	main_crops = models.CharField(max_length=255, blank=True, null=True)
	farm_size = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
	preferred_language = models.CharField(max_length=2, choices=LANGUAGE_CHOICES, default='en')
	avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
	created_at = models.DateTimeField(auto_now_add=True)

	def __str__(self):
		return f"{self.full_name} ({self.user.username})"


class Post(models.Model):
	"""Community post authored by a user, with optional image."""
	user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='posts')
	content = models.TextField(blank=True)
	image = models.ImageField(upload_to='posts/', blank=True, null=True)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['-created_at']

	def __str__(self):
		return f"Post({self.id}) by {self.user.username}"


class Comment(models.Model):
	"""User comment on a Post."""
	post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
	user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comments')
	text = models.TextField()
	# Optional parent to support threaded replies
	parent = models.ForeignKey('self', on_delete=models.CASCADE, related_name='replies', null=True, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['-created_at']

	def __str__(self):
		return f"Comment({self.id}) by {self.user.username} on Post({self.post_id})"


class PostVote(models.Model):
	"""Upvote/downvote for a Post. value=+1 (upvote) or -1 (downvote)."""
	UPVOTE = 1
	DOWNVOTE = -1

	post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='votes')
	user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='post_votes')
	value = models.SmallIntegerField(choices=((UPVOTE, 'Upvote'), (DOWNVOTE, 'Downvote')))
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		unique_together = (('post', 'user'),)

	def __str__(self):
		return f"Vote({self.value}) by {self.user.username} on Post({self.post_id})"


class CommentLike(models.Model):
	"""A simple like for a Comment (toggle)."""
	comment = models.ForeignKey(Comment, on_delete=models.CASCADE, related_name='likes')
	user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comment_likes')
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		unique_together = (('comment', 'user'),)

	def __str__(self):
		return f"Like by {self.user.username} on Comment({self.comment_id})"


class ForumPost(models.Model):
	"""Simple forum post with text and optional image."""
	user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='forum_posts')
	content = models.TextField()
	image = models.ImageField(upload_to='forum/', blank=True, null=True)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['-created_at']

	def __str__(self):
		return f"Post by {self.user.username} at {self.created_at:%Y-%m-%d %H:%M}"


class Conversation(models.Model):
	"""A chat conversation for the chatbot, per user."""
	user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='conversations')
	title = models.CharField(max_length=200, blank=True, default='')
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ['-updated_at']

	def __str__(self):
		return f"{self.title or 'Untitled'} ({self.user.username})"


class ConversationMessage(models.Model):
	"""A single message within a Conversation."""
	ROLE_CHOICES = (
		('user', 'User'),
		('assistant', 'Assistant'),
	)
	conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
	role = models.CharField(max_length=10, choices=ROLE_CHOICES)
	text = models.TextField()
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['created_at']

	def __str__(self):
		return f"{self.role} • {self.text[:30]}..."
