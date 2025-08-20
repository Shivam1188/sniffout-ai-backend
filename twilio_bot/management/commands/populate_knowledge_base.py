# twilio_bot/management/commands/populate_knowledge_base.py
from django.core.management.base import BaseCommand
from twilio_bot.models import (  # Change from myapp to twilio_bot
    KnowledgeCategory, KnowledgeItem, ServiceFeature, 
    PricingPlan, RestaurantType, FAQ, SuccessStory
)


class Command(BaseCommand):
    help = 'Populate knowledge base with initial data'
    
    def handle(self, *args, **options):
        self.stdout.write('Populating knowledge base...')
        
        # Create categories - extract just the object, not the tuple
        categories = {}
        
        # Services category
        services_cat, created = KnowledgeCategory.objects.get_or_create(
            name='Services',
            category_type='services',
            defaults={'description': 'Voice assistant services'}
        )
        categories['services'] = services_cat
        
        # Pricing category
        pricing_cat, created = KnowledgeCategory.objects.get_or_create(
            name='Pricing',
            category_type='pricing', 
            defaults={'description': 'Pricing plans and costs'}
        )
        categories['pricing'] = pricing_cat
        
        # Features category
        features_cat, created = KnowledgeCategory.objects.get_or_create(
            name='Features',
            category_type='features',
            defaults={'description': 'Service features and capabilities'}
        )
        categories['features'] = features_cat
        
        # FAQ category
        faq_cat, created = KnowledgeCategory.objects.get_or_create(
            name='FAQ',
            category_type='faq',
            defaults={'description': 'Frequently asked questions'}
        )
        categories['faq'] = faq_cat
        
        # Implementation category
        impl_cat, created = KnowledgeCategory.objects.get_or_create(
            name='Implementation',
            category_type='implementation',
            defaults={'description': 'Setup and implementation details'}
        )
        categories['implementation'] = impl_cat
        
        self.stdout.write(f'Created/found {len(categories)} categories')
        
        # Create pricing plans
        pricing_plans = [
            {
                'name': 'Basic Plan',
                'plan_type': 'basic',
                'price': '$99/month',
                'description': 'Perfect for small restaurants and cafes',
                'features': 'Up to 500 calls/month\nBasic order taking\nStandard support\nMenu integration\nBasic analytics',
                'call_limit': 'Up to 500 calls/month',
                'order': 1
            },
            {
                'name': 'Professional Plan', 
                'plan_type': 'professional',
                'price': '$299/month',
                'description': 'Ideal for growing restaurants with higher call volumes',
                'features': 'Up to 2000 calls/month\nAdvanced order taking\nReservation management\nPriority support\nAdvanced analytics dashboard\nMultilingual support',
                'call_limit': 'Up to 2000 calls/month',
                'order': 2
            },
            {
                'name': 'Enterprise Plan',
                'plan_type': 'enterprise', 
                'price': 'Custom pricing',
                'description': 'For large restaurant chains and high-volume operations',
                'features': 'Unlimited calls\nCustom integrations\nDedicated account manager\nAdvanced analytics\nCustom voice training\nAPI access\n24/7 premium support',
                'call_limit': 'Unlimited calls',
                'order': 3
            }
        ]
        
        for plan_data in pricing_plans:
            plan, created = PricingPlan.objects.get_or_create(
                name=plan_data['name'],
                defaults=plan_data
            )
            if created:
                self.stdout.write(f'Created pricing plan: {plan.name}')
        
        # Create FAQs
        faqs = [
            {
                'question': 'How does the voice assistant work?',
                'answer': 'Our AI voice assistant uses advanced natural language processing to understand customer requests, access your menu and systems in real-time, and provide accurate responses just like a trained staff member would. It can handle orders, reservations, menu questions, and general inquiries 24/7.',
                'keywords': 'how it works, voice assistant, ai, technology, natural language',
                'category': categories['faq'],
                'order': 1
            },
            {
                'question': 'How long does setup take?',
                'answer': 'We handle the complete setup process including phone system integration, menu programming, and staff training. Most restaurants are fully operational within 2-3 business days. Our technical team works with you to ensure seamless integration with your existing systems.',
                'keywords': 'setup, installation, implementation, time, integration, how long',
                'category': categories['faq'],
                'order': 2
            },
            {
                'question': 'How accurate is the system?',
                'answer': 'Our voice assistant achieves 95%+ accuracy in order taking and customer service interactions. The system continuously learns from each interaction to improve over time, and we provide regular updates to enhance performance based on your specific restaurant needs.',
                'keywords': 'accuracy, reliable, error rate, performance, quality',
                'category': categories['faq'],
                'order': 3
            },
            {
                'question': 'What languages are supported?',
                'answer': 'We currently support English, Spanish, and French, with additional languages available upon request. The system can be customized to handle multiple languages simultaneously based on your customer demographics and location.',
                'keywords': 'languages, multilingual, spanish, french, international',
                'category': categories['faq'],
                'order': 4
            },
            {
                'question': 'How much does it cost?',
                'answer': 'We offer three main plans: Basic at $99/month for up to 500 calls, Professional at $299/month for up to 2000 calls, and Enterprise with custom pricing for unlimited calls. All plans include setup, training, and ongoing support.',
                'keywords': 'cost, price, pricing, plans, how much, fees',
                'category': categories['faq'],
                'order': 5
            },
            {
                'question': 'Can it integrate with our existing POS system?',
                'answer': 'Yes! We integrate with all major POS systems including Toast, Square, Clover, and many others. Our system can directly place orders into your POS, update inventory, and sync with your existing workflow without any disruption.',
                'keywords': 'integration, pos, point of sale, toast, square, clover',
                'category': categories['faq'],
                'order': 6
            }
        ]
        
        for faq_data in faqs:
            faq, created = FAQ.objects.get_or_create(
                question=faq_data['question'],
                defaults=faq_data
            )
            if created:
                self.stdout.write(f'Created FAQ: {faq.question[:50]}...')
        
        # Create service features
        features = [
            {
                'name': '24/7 Automated Call Handling',
                'description': 'Handle customer calls round the clock without human intervention, ensuring no missed opportunities even during off-hours or peak times.',
                'category': categories['features'],
                'order': 1
            },
            {
                'name': 'Intelligent Order Taking', 
                'description': 'Accurately take complex orders with modifications, upselling suggestions, and real-time menu availability checks integrated with your POS system.',
                'category': categories['features'],
                'order': 2
            },
            {
                'name': 'Smart Reservation Management',
                'description': 'Handle booking requests, check availability, send confirmations, and manage your reservation system with intelligent scheduling.',
                'category': categories['features'],
                'order': 3
            },
            {
                'name': 'Menu Information & Recommendations',
                'description': 'Provide detailed menu information, ingredient lists, allergen warnings, and personalized recommendations based on customer preferences.',
                'category': categories['features'],
                'order': 4
            },
            {
                'name': 'Multilingual Customer Service',
                'description': 'Communicate with customers in multiple languages, expanding your reach and improving customer satisfaction across diverse communities.',
                'category': categories['features'],
                'order': 5
            },
            {
                'name': 'Real-time Analytics Dashboard',
                'description': 'Track call volumes, order patterns, customer preferences, and performance metrics with comprehensive reporting and insights.',
                'category': categories['features'],
                'order': 6
            }
        ]
        
        for feature_data in features:
            feature, created = ServiceFeature.objects.get_or_create(
                name=feature_data['name'],
                defaults=feature_data
            )
            if created:
                self.stdout.write(f'Created feature: {feature.name}')
        
        # Create restaurant types
        restaurant_types = [
            {
                'name': 'Fast Food & Quick Service',
                'description': 'High-volume, speed-focused establishments',
                'solution_details': 'Optimized for rapid order processing, upselling combos and deals, handling high call volumes during peak hours.',
                'order': 1
            },
            {
                'name': 'Fine Dining',
                'description': 'Upscale restaurants with sophisticated service',
                'solution_details': 'Elegant voice interactions, complex reservation management, dietary restriction handling, special occasion bookings.',
                'order': 2
            },
            {
                'name': 'Pizza & Delivery',
                'description': 'Pizza shops and delivery-focused restaurants',
                'solution_details': 'Address verification, delivery time estimates, order tracking integration, loyalty program management.',
                'order': 3
            },
            {
                'name': 'Family Restaurants',
                'description': 'Casual dining establishments serving families',
                'solution_details': 'Kid-friendly options, large group reservations, special dietary needs, birthday party bookings.',
                'order': 4
            }
        ]
        
        for rt_data in restaurant_types:
            rt, created = RestaurantType.objects.get_or_create(
                name=rt_data['name'],
                defaults=rt_data
            )
            if created:
                self.stdout.write(f'Created restaurant type: {rt.name}')
        
        # Create some knowledge items
        knowledge_items = [
            {
                'title': 'Voice Assistant Implementation Process',
                'content': 'Our implementation process is designed to be smooth and non-disruptive. First, we analyze your current phone system and menu. Then we configure the AI assistant with your specific offerings and preferences. Next, we integrate with your POS and reservation systems. Finally, we provide staff training and go live with full support.',
                'keywords': 'implementation, setup, process, integration, training',
                'category': categories['implementation'],
                'confidence_boost': 10,
                'order': 1
            },
            {
                'title': 'Restaurant Voice Technology Benefits',
                'content': 'Voice assistants help restaurants reduce labor costs by up to 40%, increase order accuracy to 95%+, handle multiple calls simultaneously, provide 24/7 availability, generate detailed analytics, and improve customer satisfaction through consistent service quality.',
                'keywords': 'benefits, advantages, cost savings, efficiency, labor, accuracy',
                'category': categories['services'],
                'confidence_boost': 5,
                'order': 1
            }
        ]
        
        for ki_data in knowledge_items:
            ki, created = KnowledgeItem.objects.get_or_create(
                title=ki_data['title'],
                defaults=ki_data
            )
            if created:
                self.stdout.write(f'Created knowledge item: {ki.title}')
        
        # Create success stories
        success_stories = [
            {
                'restaurant_name': 'Mario\'s Pizza Palace',
                'restaurant_type': RestaurantType.objects.filter(name__icontains='Pizza').first(),
                'story': 'After implementing our voice assistant, Mario\'s Pizza Palace saw a 40% increase in order accuracy and reduced customer wait times by 60%. They now handle 3x more calls during peak hours without hiring additional staff.',
                'metrics': '40% increase in order accuracy\n60% reduction in wait times\n300% more calls handled\n$15,000 monthly labor cost savings',
                'is_featured': True,
                'order': 1
            },
            {
                'restaurant_name': 'The Golden Spoon',
                'restaurant_type': RestaurantType.objects.filter(name__icontains='Fine').first(),
                'story': 'This upscale restaurant improved customer satisfaction scores by 25% with our multilingual voice assistant. The system elegantly handles complex reservations and dietary restrictions while maintaining their premium service standards.',
                'metrics': '25% improvement in customer satisfaction\n50% reduction in missed reservations\n30% increase in repeat customers\nMultilingual support in 3 languages',
                'is_featured': True,
                'order': 2
            }
        ]
        
        for story_data in success_stories:
            story, created = SuccessStory.objects.get_or_create(
                restaurant_name=story_data['restaurant_name'],
                defaults=story_data
            )
            if created:
                self.stdout.write(f'Created success story: {story.restaurant_name}')
        
        self.stdout.write(self.style.SUCCESS('Knowledge base populated successfully!'))
        
        # Print summary
        self.stdout.write(f'\nSummary:')
        self.stdout.write(f'- Categories: {KnowledgeCategory.objects.count()}')
        self.stdout.write(f'- FAQs: {FAQ.objects.count()}')
        self.stdout.write(f'- Pricing Plans: {PricingPlan.objects.count()}')
        self.stdout.write(f'- Features: {ServiceFeature.objects.count()}')
        self.stdout.write(f'- Restaurant Types: {RestaurantType.objects.count()}')
        self.stdout.write(f'- Knowledge Items: {KnowledgeItem.objects.count()}')
        self.stdout.write(f'- Success Stories: {SuccessStory.objects.count()}')
