from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from datetime import datetime
from .models import FarmerProfile, Post, Comment, PostVote, CommentLike, Conversation, ConversationMessage
from django.db.models import Sum, Count, Q, Prefetch
from .gemini_client import ask_gemini
from .weather_client import get_weather_for_query


def home(request):
	"""Render the landing homepage."""
	return render(request, 'home.html')


def login_view(request):
	"""Render the login page and authenticate on POST."""
	if request.user.is_authenticated and request.method == 'GET':
		return redirect('forum')
	if request.method == 'POST':
		identifier = request.POST.get('identifier')  # email or username or phone
		password = request.POST.get('password')
		user = authenticate(request, username=identifier, password=password)
		if not user:
			# Try authenticate by email mapping to username
			try:
				u = User.objects.get(email=identifier)
				user = authenticate(request, username=u.username, password=password)
			except User.DoesNotExist:
				user = None
		if user:
			auth_login(request, user)
			return redirect('forum')
		messages.error(request, 'Invalid credentials. Please try again.')
	return render(request, 'login.html')


def signup_view(request):
	"""Render and handle the signup form to create a user and profile."""
	if request.method == 'POST':
		full_name = request.POST.get('full_name')
		contact = request.POST.get('contact')  # phone or email
		email = request.POST.get('email')
		password = request.POST.get('password')
		state = request.POST.get('state')
		district_village = request.POST.get('district_village')
		farming_types = request.POST.getlist('farming_types') or request.POST.get('farming_types')
		main_crops = request.POST.get('main_crops')
		farm_size = request.POST.get('farm_size')
		preferred_language = request.POST.get('preferred_language', 'en')

		# Determine username and email
		username = email or contact
		if not username:
			messages.error(request, 'Please provide an email or mobile number.')
			return render(request, 'signup.html')

		# If account exists, abort early
		if User.objects.filter(username=username).exists():
			messages.error(request, 'An account with these details already exists.')
			return render(request, 'signup.html')

		# Create the user securely
		user = User(username=username, email=email or '')
		user.set_password(password)
		user.save()

		# Normalize farming types to comma-separated string
		if isinstance(farming_types, list):
			farming_types_str = ','.join(farming_types)
		else:
			farming_types_str = farming_types or ''

		profile = FarmerProfile.objects.create(
			user=user,
			full_name=full_name or username,
			phone=contact if (contact and contact.isdigit()) else None,
			state=state,
			district_village=district_village or None,
			farming_types=farming_types_str,
			main_crops=main_crops or None,
			farm_size=farm_size or None,
			preferred_language=preferred_language,
		)

		# Auto-login and go to dashboard
		user = authenticate(request, username=user.username, password=password)
		if user:
			auth_login(request, user)
			return redirect('forum')
		messages.success(request, 'Signup successful. Please login.')
		return redirect('login')

	return render(request, 'signup.html')


@login_required
def dashboard(request):
	"""Temporary dashboard page after login/signup."""
	# Try to load profile; it's optional for now
	profile = getattr(request.user, 'farmer_profile', None)
	def sample_weather(state_code):
		return {
			'MH': 'Sunny • 31°C', 'KA': 'Cloudy • 28°C', 'AP': 'Humid • 30°C', 'GJ': 'Dry • 33°C',
			'PB': 'Haze • 26°C', 'UP': 'Clear • 29°C', 'WB': 'Rain • 27°C', 'RJ': 'Hot • 35°C'
		}.get((profile.state if profile else '') or '', 'Clear • 29°C')

	greeting_name = (profile.full_name if profile and profile.full_name else request.user.username)
	today_str = datetime.now().strftime('%A, %d %B %Y')
	weather_str = sample_weather(profile.state if profile else '')

	stats = {
		'posts': 12,
		'scheme': 'PM-Kisan installment announced',
		'weather': weather_str,
		'alerts': 2,
	}

	community_feed = [
		{'title': 'Best paddy variety for Kharif?', 'author': 'Anita', 'time': '2h ago', 'tag': 'Rice'},
		{'title': 'Organic pest control for cotton', 'author': 'Vijay', 'time': '4h ago', 'tag': 'Cotton'},
		{'title': 'Drip irrigation tips', 'author': 'Harpreet', 'time': '1d ago', 'tag': 'Irrigation'},
	]

	learning_items = [
		{'title': 'Soil health basics', 'type': 'Article'},
		{'title': 'Integrated Pest Management', 'type': 'Video'},
		{'title': 'Market linkage 101', 'type': 'Guide'},
	]

	schemes = [
		{'title': 'Fasal Bima Yojana', 'state': 'All India'},
		{'title': 'State drip irrigation subsidy', 'state': (profile.state if profile else 'Your State')},
	]

	ctx = {
		'profile': profile,
		'greeting_name': greeting_name,
		'today_str': today_str,
		'weather_str': weather_str,
		'stats': stats,
		'community_feed': community_feed,
		'learning_items': learning_items,
		'schemes': schemes,
	}
	return render(request, 'dashboard.html', ctx)


def logout_view(request):
	auth_logout(request)
	return redirect('home')


@login_required
def update_profile_api(request):
	if request.method != 'POST':
		return JsonResponse({'error': 'Method not allowed'}, status=405)
	import json
	try:
		data = request.POST.dict()
		if not data:
			data = json.loads(request.body.decode('utf-8') or '{}')
	except Exception:
		data = {}

	prof, _ = FarmerProfile.objects.get_or_create(
		user=request.user,
		defaults={'full_name': request.user.username, 'state': data.get('state') or 'MH'}
	)

	# Update simple fields if present
	for field in ['full_name', 'district_village', 'main_crops', 'preferred_language']:
		if field in data and data[field] is not None:
			setattr(prof, field, data[field])

	if 'state' in data and data['state']:
		prof.state = data['state']

	if 'farm_size' in data and str(data['farm_size']).strip() != '':
		try:
			prof.farm_size = float(data['farm_size'])
		except Exception:
			pass

	# farming_types can be list or comma string
	ft = data.get('farming_types')
	if isinstance(ft, list):
		prof.farming_types = ','.join(ft)
	elif isinstance(ft, str):
		prof.farming_types = ft

	# phone/contact
	if 'phone' in data:
		prof.phone = data['phone']

	# Avatar image upload if provided via multipart form
	avatar_file = request.FILES.get('avatar')
	if avatar_file is not None:
		prof.avatar = avatar_file

	prof.save()
	return JsonResponse({
		'ok': True,
		'profile': {
			'full_name': prof.full_name,
			'state': prof.state,
			'district_village': prof.district_village,
			'farming_types': prof.farming_types,
			'main_crops': prof.main_crops,
			'farm_size': float(prof.farm_size) if prof.farm_size is not None else None,
			'preferred_language': prof.preferred_language,
			'phone': prof.phone,
			'avatar_url': (prof.avatar.url if prof.avatar else None),
		}
	})


@login_required
def forum(request):
	profile = getattr(request.user, 'farmer_profile', None)
	# Annotate comments and replies with like counts
	from django.db.models import Count as DJCount
	comments_qs = Comment.objects.select_related('user').annotate(likes_count=DJCount('likes')).order_by('-created_at')
	posts_qs = (
		Post.objects.select_related('user')
		.annotate(
			score=Sum('votes__value', default=0),
			upvotes=Count('votes', filter=Q(votes__value=PostVote.UPVOTE)),
			downvotes=Count('votes', filter=Q(votes__value=PostVote.DOWNVOTE)),
			comments_count=Count('comments'),
		)
		# prefetch only top-level comments; each brings its replies annotated with like counts
		.prefetch_related(
			Prefetch(
				'comments',
				queryset=comments_qs.filter(parent__isnull=True).prefetch_related(
					Prefetch('replies', queryset=comments_qs.order_by('-created_at'))
				)
			)
		)
	)

	posts = list(posts_qs)
	post_ids = [p.id for p in posts]
	my_votes = {}
	if request.user.is_authenticated and post_ids:
		my_votes = {v.post_id: v.value for v in PostVote.objects.filter(user=request.user, post_id__in=post_ids)}
	# Preload which comments current user has liked (for UI state)
	my_comment_likes = set()
	if request.user.is_authenticated and post_ids:
		my_comment_likes = set(
			CommentLike.objects.filter(user=request.user, comment__post_id__in=post_ids).values_list('comment_id', flat=True)
		)

	popular = ['Pest control', 'Irrigation', 'Soil testing', 'Market prices']
	ctx = {'profile': profile, 'posts': posts, 'popular': popular, 'my_votes': my_votes, 'my_comment_likes': my_comment_likes}
	return render(request, 'forum.html', ctx)


@login_required
@require_POST
def forum_vote(request):
	post_id = request.POST.get('post_id')
	action = (request.POST.get('action') or '').strip()  # 'up', 'down', 'clear'
	if not post_id or action not in {'up', 'down', 'clear'}:
		return JsonResponse({'ok': False, 'error': 'Invalid parameters'}, status=400)
	try:
		post = Post.objects.get(id=post_id)
	except Post.DoesNotExist:
		return JsonResponse({'ok': False, 'error': 'Post not found'}, status=404)

	current_val = None
	try:
		vote = PostVote.objects.get(post=post, user=request.user)
		current_val = vote.value
	except PostVote.DoesNotExist:
		vote = None

	if action == 'clear':
		if vote:
			vote.delete()
	else:
		new_val = PostVote.UPVOTE if action == 'up' else PostVote.DOWNVOTE
		if vote:
			if vote.value == new_val:
				# toggle off
				vote.delete()
			else:
				vote.value = new_val
				vote.save()
		else:
			PostVote.objects.create(post=post, user=request.user, value=new_val)

	# Recalculate counts
	agg = PostVote.objects.filter(post=post).aggregate(
		upvotes=Count('id', filter=Q(value=PostVote.UPVOTE)),
		downvotes=Count('id', filter=Q(value=PostVote.DOWNVOTE)),
		score=Sum('value', default=0),
	)
	try:
		my_vote = PostVote.objects.get(post=post, user=request.user).value
	except PostVote.DoesNotExist:
		my_vote = 0

	return JsonResponse({'ok': True, 'post_id': post.id, 'upvotes': agg['upvotes'] or 0, 'downvotes': agg['downvotes'] or 0, 'score': agg['score'] or 0, 'my_vote': my_vote})


@login_required
@require_POST
def forum_comment(request):
	post_id = request.POST.get('post_id')
	text = (request.POST.get('text') or '').strip()
	parent_id = request.POST.get('parent_id')
	if not post_id or not text:
		return JsonResponse({'ok': False, 'error': 'Post and text are required'}, status=400)
	try:
		post = Post.objects.get(id=post_id)
	except Post.DoesNotExist:
		return JsonResponse({'ok': False, 'error': 'Post not found'}, status=404)

	parent = None
	if parent_id:
		try:
			parent = Comment.objects.get(id=parent_id, post=post)
		except Comment.DoesNotExist:
			return JsonResponse({'ok': False, 'error': 'Parent comment not found'}, status=404)

	c = Comment.objects.create(post=post, user=request.user, text=text, parent=parent)
	return JsonResponse({
		'ok': True,
		'comment': {
			'id': c.id,
			'post_id': post.id,
			'user': request.user.username,
			'text': c.text,
			'created_at': c.created_at.strftime('%Y-%m-%d %H:%M'),
			'parent_id': c.parent_id,
		}
	})


@login_required
@require_POST
def forum_comment_like(request):
	comment_id = request.POST.get('comment_id')
	if not comment_id:
		return JsonResponse({'ok': False, 'error': 'Comment id required'}, status=400)
	try:
		c = Comment.objects.get(id=comment_id)
	except Comment.DoesNotExist:
		return JsonResponse({'ok': False, 'error': 'Comment not found'}, status=404)

	# toggle like
	liked = False
	try:
		cl = CommentLike.objects.get(comment=c, user=request.user)
		# if exists, unlike
		cl.delete()
		liked = False
	except CommentLike.DoesNotExist:
		CommentLike.objects.create(comment=c, user=request.user)
		liked = True

	# updated count
	likes_count = CommentLike.objects.filter(comment=c).count()
	return JsonResponse({'ok': True, 'comment_id': c.id, 'liked': liked, 'likes': likes_count})


@login_required
def chatbot(request):
	profile = getattr(request.user, 'farmer_profile', None)
	# Build language dropdown options (code, label displayed in native script)
	languages = [
		('en', 'English'),
		('hi', 'हिन्दी'),
		('mr', 'मराठी'),
		('ta', 'தமிழ்'),
		('te', 'తెలుగు'),
		('bn', 'বাংলা'),
		('gu', 'ગુજરાતી'),
		('pa', 'ਪੰਜਾਬੀ'),
		('ml', 'മലയാളം'),
		('kn', 'ಕನ್ನಡ'),
	]
	# Default selected from profile preference if available, else English
	selected_lang = (profile.preferred_language if profile and profile.preferred_language else 'en')
	# Load conversations for sidebar
	conversations = list(Conversation.objects.filter(user=request.user).only('id', 'title', 'updated_at')[:50])
	# If a conversation is selected via query param, load its messages
	conv_id = request.GET.get('c')
	chat_history = []
	active_conversation = None
	if conv_id:
		try:
			active_conversation = Conversation.objects.get(id=conv_id, user=request.user)
			for m in active_conversation.messages.all():
				chat_history.append({'role': m.role, 'text': m.text})
		except Conversation.DoesNotExist:
			active_conversation = None
	return render(request, 'chatbot.html', {
		'profile': profile,
		'languages': languages,
		'selected_lang': selected_lang,
		'chat_history': chat_history,
		'conversations': conversations,
		'active_conversation': active_conversation,
	})


@login_required
@require_POST
def chatbot_api(request):
	"""JSON API endpoint: accepts 'message' and optional 'image' and returns model reply."""
	message = (request.POST.get('message') or '').strip()
	image = request.FILES.get('image')
	lang_code = (request.POST.get('language') or '').strip()
	conv_id = (request.POST.get('conversation_id') or '').strip()

	if not message and not image:
		return JsonResponse({"ok": False, "error": "Please provide a message or an image."}, status=400)

	try:
		# Prepare a readable language name from code
		lang_map = {
			'en': 'English', 'hi': 'Hindi', 'mr': 'Marathi', 'ta': 'Tamil', 'te': 'Telugu',
			'bn': 'Bengali', 'gu': 'Gujarati', 'pa': 'Punjabi', 'ml': 'Malayalam', 'kn': 'Kannada'
		}
		language = lang_map.get(lang_code, lang_code or None)

		# Resolve or create conversation
		conversation = None
		if conv_id:
			try:
				conversation = Conversation.objects.get(id=conv_id, user=request.user)
			except Conversation.DoesNotExist:
				conversation = None
		if conversation is None:
			# Create new with title from first user message or image
			title = (message[:60] + ('…' if len(message) > 60 else '')) if message else 'Image chat'
			conversation = Conversation.objects.create(user=request.user, title=title)

		# Persist user message
		if message:
			ConversationMessage.objects.create(conversation=conversation, role='user', text=message)

		# Build history for model (last 12)
		msgs = list(conversation.messages.order_by('-created_at').values('role', 'text')[:12])
		msgs.reverse()
		text, raw = ask_gemini(message, image, language=language, history=msgs)

		# Persist assistant reply
		ConversationMessage.objects.create(conversation=conversation, role='assistant', text=text)

		return JsonResponse({"ok": True, "reply": text, "conversation_id": conversation.id, "title": conversation.title})
	except Exception as e:
		return JsonResponse({"ok": False, "error": str(e)}, status=500)


@login_required
def learning(request):
	profile = getattr(request.user, 'farmer_profile', None)
	items = [
		{'title': 'Basics of Organic Farming', 'thumb': 'https://images.unsplash.com/photo-1500937386664-56ed8efc5f3f?auto=format&fit=crop&w=400&q=60'},
		{'title': 'How to Test Soil Fertility at Home', 'thumb': 'https://images.unsplash.com/photo-1599058945522-58f12ec2a975?auto=format&fit=crop&w=400&q=60'},
		{'title': 'Modern Irrigation Techniques', 'thumb': 'https://images.unsplash.com/photo-1501004318641-b39e6451bec6?auto=format&fit=crop&w=400&q=60'},
		{'title': 'Integrated Pest Management', 'thumb': 'https://images.unsplash.com/photo-1543336668-cc2564b906b5?auto=format&fit=crop&w=400&q=60'},
	]
	return render(request, 'learning.html', {'profile': profile, 'items': items})


@login_required
def schemes(request):
	profile = getattr(request.user, 'farmer_profile', None)
	data = [
		{'title': 'PM-Kisan Samman Nidhi Yojana', 'desc': 'Income support to all farmer families across the country.'},
		{'title': 'Soil Health Card Scheme', 'desc': 'Promotes soil test-based nutrient management.'},
		{'title': 'Pradhan Mantri Fasal Bima Yojana (PMFBY)', 'desc': 'Crop insurance scheme for farmers.'},
	]
	return render(request, 'schemes.html', {'profile': profile, 'schemes': data})


@login_required
def weather_updates(request):
	profile = getattr(request.user, 'farmer_profile', None)
	q = request.GET.get('q', '').strip()
	lat = request.GET.get('lat')
	lon = request.GET.get('lon')
	result = None
	error = None
	try:
		if lat and lon:
			result = get_weather_for_query(lat=float(lat), lon=float(lon))
		elif q:
			result = get_weather_for_query(query=q)
		elif profile and profile.district_village:
			result = get_weather_for_query(query=profile.district_village)
		elif profile and profile.get_state_display():
			result = get_weather_for_query(query=profile.get_state_display())
	except Exception as e:
		error = str(e)

	ctx = {
		'profile': profile,
		'q': q,
		'result': result,
		'error': error,
	}
	return render(request, 'weather.html', ctx)


@login_required
def profile_page(request):
	# Ensure a profile exists
	profile, _ = FarmerProfile.objects.get_or_create(
		user=request.user,
		defaults={
			'full_name': request.user.get_full_name() or request.user.username,
			'state': 'MH',
			'preferred_language': 'en',
		}
	)

	# Prepare readable farming types
	ft_codes = [c.strip() for c in (profile.farming_types or '').split(',') if c.strip()]
	ft_map = dict(FarmerProfile.FARMING_CHOICES)
	farming_types_list = [ft_map.get(code, code) for code in ft_codes]

	user_info = {
		'username': request.user.username,
		'email': request.user.email,
		'date_joined': request.user.date_joined,
		'last_login': request.user.last_login,
	}

	# Handle create post (moved from forum)
	if request.method == 'POST':
		content = (request.POST.get('content') or '').strip()
		image = request.FILES.get('image')
		if not content and not image:
			messages.error(request, 'Please write something or add an image to post.')
		else:
			Post.objects.create(user=request.user, content=content, image=image)
			messages.success(request, 'Your post has been published.')
			return redirect('profile_page')

	ctx = {
		'profile': profile,
		'farming_types_list': farming_types_list,
		'user_info': user_info,
		# Annotate user's posts with comment and like counts for display
		'my_posts': Post.objects.filter(user=request.user)
			.select_related('user')
			.annotate(
				comment_count=Count('comments'),
				like_count=Count('votes', filter=Q(votes__value=PostVote.UPVOTE))
			),
	}
	return render(request, 'profile.html', ctx)


@login_required
def settings_page(request):
	profile = getattr(request.user, 'farmer_profile', None)
	return render(request, 'settings.html', {'profile': profile})
