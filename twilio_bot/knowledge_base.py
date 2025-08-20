# knowledge_base.py
import json
import re
from typing import List, Dict, Any
from fuzzywuzzy import fuzz
from django.db import models
from channels.db import database_sync_to_async
import logging

from .models import (
    KnowledgeCategory, KnowledgeItem, ServiceFeature, 
    PricingPlan, RestaurantType, FAQ, SuccessStory, TechnicalSpec
)

logger = logging.getLogger(__name__)


class RestaurantKnowledgeBase:
    def __init__(self):
        # Cache frequently accessed data
        self._cache = {}
        self._cache_timeout = 300  # 5 minutes
    
    async def search_knowledge(self, query: str) -> Dict[str, Any]:
        """Search knowledge base for relevant information from database"""
        query_lower = query.lower()
        results = {"matches": [], "confidence": 0}
        
        # Check for goodbye/farewell messages first
        goodbye_keywords = [
            "bye", "goodbye", "good bye", "see you", "thanks", "thank you", 
            "that's all", "thats all", "no more questions", "i'm done", "im done",
            "have a good day", "take care", "later", "farewell", "done", "finished"
        ]
        
        if any(keyword in query_lower for keyword in goodbye_keywords):
            results["matches"].append({
                "type": "goodbye",
                "content": {
                    "message": "goodbye",
                    "user_query": query
                },
                "confidence": 100  # High confidence for goodbye
            })
            results["confidence"] = 100
            return results
        
        # Continue with regular knowledge base search
        matches = []
        
        # Search FAQs first (usually highest confidence)
        faq_matches = await self._search_faqs(query_lower)
        matches.extend(faq_matches)
        
        # Search pricing plans
        pricing_matches = await self._search_pricing(query_lower)
        matches.extend(pricing_matches)
        
        # Search knowledge items
        knowledge_matches = await self._search_knowledge_items(query_lower)
        matches.extend(knowledge_matches)
        
        # Search service features
        feature_matches = await self._search_features(query_lower)
        matches.extend(feature_matches)
        
        # Search success stories
        story_matches = await self._search_success_stories(query_lower)
        matches.extend(story_matches)
        
        if matches:
            # Sort by confidence and take top matches
            matches.sort(key=lambda x: x["confidence"], reverse=True)
            results["matches"] = matches[:3]  # Limit to top 3
            results["confidence"] = matches[0]["confidence"]
        
        return results

    
    @database_sync_to_async
    def _search_faqs(self, query_lower: str) -> List[Dict]:
        """Search FAQ entries"""
        matches = []
        
        # Keywords for FAQ categories
        pricing_keywords = ["price", "cost", "plan", "pricing", "how much", "fee"]
        setup_keywords = ["setup", "install", "implement", "start", "begin", "integration"]
        feature_keywords = ["feature", "benefit", "capability", "what can", "how does"]
        
        faqs = FAQ.objects.filter(is_active=True).select_related('category')
        
        for faq in faqs:
            confidence = 0
            
            # Check question similarity
            question_similarity = fuzz.partial_ratio(query_lower, faq.question.lower())
            if question_similarity > 60:
                confidence = max(confidence, question_similarity)
            
            # Check keywords
            for keyword in faq.get_keywords_list():
                if keyword in query_lower:
                    confidence = max(confidence, 85)
            
            # Category-specific keyword matching
            if faq.category.category_type == 'faq':
                if any(kw in query_lower for kw in pricing_keywords) and 'price' in faq.question.lower():
                    confidence = max(confidence, 90)
                elif any(kw in query_lower for kw in setup_keywords) and 'setup' in faq.question.lower():
                    confidence = max(confidence, 90)
                elif any(kw in query_lower for kw in feature_keywords) and 'feature' in faq.question.lower():
                    confidence = max(confidence, 85)
            
            if confidence > 60:
                matches.append({
                    "type": "faq",
                    "content": {
                        "question": faq.question,
                        "answer": faq.answer,
                        "category": faq.category.name
                    },
                    "confidence": confidence
                })
        
        return matches
    

    def get_features_list(self):
        """Return features as a list"""
        if self.features:
            # Split by newlines and filter out empty strings
            features_list = [f.strip() for f in self.features.split('\n') if f.strip()]
            return features_list
        return []


    @database_sync_to_async
    def _search_pricing(self, query_lower: str) -> List[Dict]:
        """Search pricing plans"""
        matches = []
        pricing_keywords = ["price", "cost", "plan", "pricing", "how much", "fee", "basic", "professional", "enterprise"]
        
        if any(keyword in query_lower for keyword in pricing_keywords):
            plans = PricingPlan.objects.filter(is_active=True).order_by('order')
            
            if plans.exists():
                plans_data = []
                for plan in plans:
                    # Fix: Make sure features is handled correctly
                    features_list = plan.get_features_list()  # This returns a list of strings
                    
                    plan_dict = {
                        "name": plan.name,
                        "price": plan.price,
                        "features": features_list,  # This is already a list of strings
                        "call_limit": plan.call_limit or "",
                        "plan_type": plan.plan_type,
                        "description": plan.description or ""
                    }
                    plans_data.append(plan_dict)
                
                matches.append({
                    "type": "pricing",
                    "content": {
                        "plans": plans_data
                    },
                    "confidence": 95
                })
        
        return matches


    @database_sync_to_async
    def _search_knowledge_items(self, query_lower: str) -> List[Dict]:
        """Search knowledge items"""
        matches = []
        
        items = KnowledgeItem.objects.filter(
            is_active=True
        ).select_related('category').order_by('-confidence_boost', 'order')
        
        for item in items:
            confidence = 0
            
            # Title similarity
            title_similarity = fuzz.partial_ratio(query_lower, item.title.lower())
            if title_similarity > 50:
                confidence = max(confidence, title_similarity)
            
            # Content similarity (partial)
            content_similarity = fuzz.partial_ratio(query_lower, item.content[:200].lower())
            if content_similarity > 40:
                confidence = max(confidence, content_similarity - 10)  # Slightly lower for content
            
            # Keyword matching
            for keyword in item.get_keywords_list():
                if keyword in query_lower:
                    confidence = max(confidence, 80)
            
            # Apply confidence boost
            confidence += item.confidence_boost
            confidence = max(0, min(100, confidence))  # Clamp between 0-100
            
            if confidence > 50:
                matches.append({
                    "type": "knowledge_item",
                    "content": {
                        "title": item.title,
                        "content": item.content,
                        "category": item.category.name,
                        "category_type": item.category.category_type
                    },
                    "confidence": confidence
                })
        
        return matches
    
    @database_sync_to_async
    def _search_features(self, query_lower: str) -> List[Dict]:
        """Search service features"""
        matches = []
        feature_keywords = ["feature", "benefit", "capability", "what can", "how does", "voice", "assistant"]
        
        if any(keyword in query_lower for keyword in feature_keywords):
            features = ServiceFeature.objects.filter(
                is_active=True
            ).select_related('category').order_by('order')
            
            if features.exists():
                features_data = []
                for feature in features:
                    features_data.append({
                        "name": feature.name,
                        "description": feature.description,
                        "category": feature.category.name
                    })
                
                matches.append({
                    "type": "features",
                    "content": {
                        "features": features_data
                    },
                    "confidence": 85
                })
        
        return matches
    
    @database_sync_to_async
    def _search_success_stories(self, query_lower: str) -> List[Dict]:
        """Search success stories"""
        matches = []
        story_keywords = ["success", "story", "case", "example", "customer", "result", "improvement"]
        
        if any(keyword in query_lower for keyword in story_keywords):
            stories = SuccessStory.objects.filter(
                is_active=True
            ).select_related('restaurant_type').order_by('-is_featured', 'order')[:3]
            
            if stories.exists():
                stories_data = []
                for story in stories:
                    stories_data.append({
                        "restaurant_name": story.restaurant_name,
                        "restaurant_type": story.restaurant_type.name if story.restaurant_type else "Restaurant",
                        "story": story.story,
                        "metrics": story.get_metrics_list()
                    })
                
                matches.append({
                    "type": "success_stories",
                    "content": {
                        "stories": stories_data
                    },
                    "confidence": 80
                })
        
        return matches
        
    def format_response(self, matches: List[Dict], query: str) -> str:
        """Format knowledge base results into a conversational response"""
        if not matches:
            return "I'd be happy to help you learn about our restaurant voice assistant services. Could you please ask me something specific about our AI voice solutions for restaurants?"
        
        # Sort by confidence
        matches.sort(key=lambda x: x["confidence"], reverse=True)
        best_match = matches[0]
        
        try:
            if best_match["type"] == "faq":
                return best_match["content"]["answer"]
            
            elif best_match["type"] == "pricing":
                content = best_match.get("content", {})
                plans = content.get("plans", [])
                
                if not isinstance(plans, list) or len(plans) == 0:
                    return "We offer multiple pricing plans. Let me get the specific pricing details for you."
                
                # Check if user is asking about a specific plan
                query_lower = query.lower()
                
                # Find specific plan if mentioned
                requested_plan = None
                if "basic" in query_lower:
                    requested_plan = next((p for p in plans if p.get('plan_type') == 'basic'), None)
                elif "professional" in query_lower or "pro" in query_lower:
                    requested_plan = next((p for p in plans if p.get('plan_type') == 'professional'), None)
                elif "enterprise" in query_lower:
                    requested_plan = next((p for p in plans if p.get('plan_type') == 'enterprise'), None)
                
                # If specific plan requested, provide detailed info
                if requested_plan:
                    plan_name = requested_plan.get('name', 'Plan')
                    plan_price = requested_plan.get('price', 'Contact us')
                    plan_features = requested_plan.get('features', [])
                    plan_call_limit = requested_plan.get('call_limit', '')
                    
                    features_text = ""
                    if plan_features and len(plan_features) > 0:
                        if len(plan_features) <= 3:
                            features_text = f"Key features include: {', '.join(plan_features)}."
                        else:
                            features_text = f"Key features include: {', '.join(plan_features[:3])}, and {plan_features[3]}."
                    
                    call_limit_text = f" This plan supports {plan_call_limit}." if plan_call_limit else ""
                    
                    return f"The {plan_name} is priced at {plan_price}.{call_limit_text} {features_text} Would you like to know more about this plan or compare it with others?"
                
                # Otherwise, provide overview of all plans
                else:
                    if len(plans) >= 3:
                        # Fix the indexing issue
                        plan_summaries = []
                        for i, plan in enumerate(plans[:3]):
                            if isinstance(plan, dict):
                                name = plan.get('name', f'Plan {i+1}')
                                price = plan.get('price', 'Contact us')
                                plan_summaries.append(f"{name} at {price}")
                        
                        if len(plan_summaries) == 3:
                            return f"We offer three main pricing plans: {plan_summaries[0]}, {plan_summaries[1]}, and {plan_summaries}. Which plan would you like detailed information about?"
                        else:
                            return "We offer Basic at $99/month, Professional at $299/month, and Enterprise with custom pricing. Which plan interests you most?"
                    
                    elif len(plans) > 0:
                        first_plan = plans
                        if isinstance(first_plan, dict):
                            first_price = first_plan.get('price', 'Contact us')
                            return f"We offer {len(plans)} pricing plans starting from {first_price}. Would you like details about our plans and features?"
                        else:
                            return "We have several pricing options available. Would you like specific details?"
                    
                    return "We have several pricing options available. Would you like me to get specific pricing information for you?"
            
            elif best_match["type"] == "knowledge_item":
                content = best_match["content"]
                return f"{content['content'][:300]}{'...' if len(content['content']) > 300 else ''}"
            
            elif best_match["type"] == "features":
                features = best_match["content"]["features"][:4]
                if features:
                    feature_names = []
                    for f in features:
                        if isinstance(f, dict) and "name" in f:
                            feature_names.append(f["name"])
                        elif isinstance(f, str):
                            feature_names.append(f)
                    
                    if len(feature_names) >= 3:
                        return f"Our voice assistant includes key features like {', '.join(feature_names[:3])}{', and ' + feature_names[3] if len(feature_names) > 3 else ''}. Would you like details about any specific feature?"
                    else:
                        return f"Our voice assistant includes features like {', '.join(feature_names)}. Would you like more details about these capabilities?"
                else:
                    return "Our voice assistant has many powerful features. Would you like me to tell you about them?"
            
            elif best_match["type"] == "success_stories":
                stories = best_match["content"]["stories"]
                if stories and len(stories) > 0:
                    story = stories[0]
                    return f"Here's a great example: {story['restaurant_name']} {story['story'][:200]}{'...' if len(story['story']) > 200 else ''} Would you like to hear more success stories?"
                else:
                    return "We have many success stories from restaurants. Would you like to hear some examples?"
            
            return "I have information about that topic. Could you be more specific about what you'd like to know regarding our restaurant voice assistant services?"
            
        except Exception as e:
            logger.error(f"Error formatting response: {e}", exc_info=True)
            
            # Provide specific fallback based on match type
            match_type = best_match.get("type", "unknown")
            if match_type == "pricing":
                return "We offer three pricing tiers: Basic at $99/month for smaller restaurants, Professional at $299/month for growing businesses, and Enterprise with custom pricing for larger operations. Which would you like to know more about?"
            else:
                return "I have information about that topic, but I'm having trouble formatting the response right now. Could you try asking in a different way?"
