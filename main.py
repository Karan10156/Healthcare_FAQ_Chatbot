from flask import Flask, render_template, request, jsonify, session
import json
import spacy
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import re
from collections import Counter
import string
import uuid
from datetime import datetime
import os
import pytz

app = Flask(__name__)
app.secret_key = 'healthcare_chatbot_secret_key_2024'

# Chatbot identity
CHATBOT_NAME = "Dr. Alex"
CHATBOT_PERSONALITY = {
    'en': f"Hello! I'm {CHATBOT_NAME}, your AI healthcare assistant.",
    'es': f"¡Hola! Soy {CHATBOT_NAME}, tu asistente de salud con IA.",
    'hi': f"नमस्ते! मैं {CHATBOT_NAME} हूं, आपका AI स्वास्थ्य सहायक।"
}

# Chat history storage (in production, use a proper database)
chat_histories = {}

# Load spaCy model
try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    print("spaCy model not found. Install with: python -m spacy download en_core_web_sm")
    nlp = None

# Load FAQ data with multilingual support
def load_faq_data():
    try:
        with open('faq_data.json', 'r', encoding='utf-8') as f:
            english_data = json.load(f)
    except FileNotFoundError:
        english_data = []
    
    try:
        with open('faq_data_es.json', 'r', encoding='utf-8') as f:
            spanish_data = json.load(f)
    except FileNotFoundError:
        spanish_data = []
    
    try:
        with open('faq_data_hi.json', 'r', encoding='utf-8') as f:
            hindi_data = json.load(f)
    except FileNotFoundError:
        hindi_data = []
    
    return {
        'en': english_data,
        'es': spanish_data,
        'hi': hindi_data
    }

multilingual_faq = load_faq_data()
faq_data = multilingual_faq['en']  # Default to English
faq_questions = [item['question'] for item in faq_data]
faq_answers = [item['answer'] for item in faq_data]

# Initialize TF-IDF vectorizer with enhanced parameters
vectorizer = TfidfVectorizer(
    stop_words='english', 
    lowercase=True,
    ngram_range=(1, 2),  # Include bigrams for better matching
    max_features=5000,
    min_df=1,
    max_df=0.95
)

def preprocess_text(text):
    """Enhanced text preprocessing using spaCy"""
    if nlp:
        doc = nlp(text.lower())
        # Extract lemmatized tokens, excluding stop words, punctuation, and spaces
        tokens = [
            token.lemma_ for token in doc 
            if not token.is_stop 
            and not token.is_punct 
            and not token.is_space 
            and token.is_alpha 
            and len(token.text) > 2
        ]
        return ' '.join(tokens)
    else:
        # Enhanced fallback preprocessing without spaCy
        text = text.lower()
        # Remove punctuation
        text = text.translate(str.maketrans('', '', string.punctuation))
        # Split and filter words
        words = [word for word in text.split() if len(word) > 2]
        return ' '.join(words)

if faq_questions:
    # Preprocess all FAQ questions
    processed_questions = [preprocess_text(q) for q in faq_questions]
    tfidf_matrix = vectorizer.fit_transform(processed_questions)

def extract_keywords(text):
    """Extract important keywords from user input"""
    if nlp:
        doc = nlp(text.lower())
        keywords = []
        for token in doc:
            if (not token.is_stop and 
                not token.is_punct and 
                token.is_alpha and 
                len(token.text) > 2):
                keywords.append(token.lemma_)
        return keywords
    else:
        # Fallback keyword extraction
        text = text.lower()
        text = text.translate(str.maketrans('', '', string.punctuation))
        words = [word for word in text.split() if len(word) > 2]
        return words

def enhanced_similarity_search(user_input, threshold=0.15):
    """Enhanced similarity search with multiple matching strategies"""
    if not faq_questions:
        return None, 0, "No FAQ data available"

    # Strategy 1: TF-IDF Cosine Similarity
    processed_input = preprocess_text(user_input)
    input_vector = vectorizer.transform([processed_input])
    similarities = cosine_similarity(input_vector, tfidf_matrix).flatten()

    # Strategy 2: Keyword matching boost
    user_keywords = set(extract_keywords(user_input))
    keyword_scores = []

    for i, question in enumerate(faq_questions):
        question_keywords = set(extract_keywords(question))
        if user_keywords and question_keywords:
            intersection = user_keywords.intersection(question_keywords)
            keyword_score = len(intersection) / len(user_keywords.union(question_keywords))
            keyword_scores.append(keyword_score)
        else:
            keyword_scores.append(0)

    # Combine scores with weights
    combined_scores = []
    for i in range(len(similarities)):
        tfidf_score = similarities[i]
        keyword_score = keyword_scores[i]
        # Weighted combination: 70% TF-IDF, 30% keyword matching
        combined_score = 0.7 * tfidf_score + 0.3 * keyword_score
        combined_scores.append(combined_score)

    best_match_idx = np.argmax(combined_scores)
    best_similarity = combined_scores[best_match_idx]

    if best_similarity >= threshold:
        confidence = min(best_similarity * 100, 95)  # Cap confidence at 95%
        return faq_answers[best_match_idx], best_similarity, f"Match confidence: {confidence:.1f}%"

    return None, best_similarity, f"Low confidence match: {best_similarity*100:.1f}%"

def detect_language(text):
    """Simple language detection for Spanish, Hindi vs English"""
    spanish_keywords = ['qué', 'cómo', 'cuál', 'dónde', 'cuándo', 'por qué', 'síntomas', 'dolor', 'medicamento', 'doctor', 'salud', 'hospital', 'enfermedad']
    hindi_keywords = ['क्या', 'कैसे', 'कौन', 'कहाँ', 'कब', 'क्यों', 'लक्षण', 'दर्द', 'दवा', 'डॉक्टर', 'स्वास्थ्य', 'अस्पताल', 'बीमारी', 'मैं', 'है', 'हैं', 'का', 'की', 'के']
    text_lower = text.lower()
    
    spanish_count = sum(1 for word in spanish_keywords if word in text_lower)
    hindi_count = sum(1 for word in hindi_keywords if word in text)  # Don't lowercase for Hindi
    
    if hindi_count > 0:
        return 'hi'
    elif spanish_count > 0:
        return 'es'
    else:
        return 'en'

def get_or_create_session():
    """Get or create user session for chat history"""
    if 'user_id' not in session:
        session['user_id'] = str(uuid.uuid4())
        session['language'] = 'en'
        chat_histories[session['user_id']] = []
    return session['user_id']

def save_message_to_history(user_id, message, response, language='en'):
    """Save conversation to chat history with IST timezone"""
    if user_id not in chat_histories:
        chat_histories[user_id] = []
    
    # Get current time in IST
    ist = pytz.timezone('Asia/Kolkata')
    ist_time = datetime.now(ist)
    
    chat_histories[user_id].append({
        'timestamp': ist_time.isoformat(),
        'user_message': message,
        'bot_response': response,
        'language': language,
        'ist_display': ist_time.strftime('%Y-%m-%d %H:%M:%S IST')
    })
    
    # Keep only last 50 messages per user
    if len(chat_histories[user_id]) > 50:
        chat_histories[user_id] = chat_histories[user_id][-50:]

def get_chat_history(user_id):
    """Retrieve chat history for user"""
    return chat_histories.get(user_id, [])

def setup_language_vectorizer(language='en'):
    """Setup TF-IDF vectorizer for specific language"""
    if language == 'es':
        try:
            nlp_es = spacy.load("es_core_news_sm")
            stop_words = 'spanish'
        except OSError:
            stop_words = ['el', 'la', 'de', 'que', 'y', 'a', 'en', 'un', 'es', 'se', 'no', 'te', 'lo', 'le', 'da', 'su', 'por', 'son', 'con', 'para', 'al', 'del', 'los', 'las']
    elif language == 'hi':
        # Hindi stop words and common words
        stop_words = ['का', 'की', 'के', 'में', 'से', 'को', 'पर', 'है', 'हैं', 'था', 'थी', 'थे', 'होना', 'होने', 'वाला', 'वाली', 'वाले', 'यह', 'वह', 'इस', 'उस', 'और', 'या', 'तो', 'जो', 'कि', 'लिए', 'साथ', 'बाद', 'पहले', 'दौरान', 'तक', 'द्वारा']
    else:
        stop_words = 'english'
    
    return TfidfVectorizer(
        stop_words=stop_words,
        lowercase=True,
        ngram_range=(1, 2),
        max_features=5000,
        min_df=1,
        max_df=0.95
    )

def generate_fallback_response(user_input, language='en'):
    """Generate helpful fallback response for unmatched queries with bilingual support"""
    keywords = extract_keywords(user_input)

    if language == 'es':
        health_topics = {
            'síntomas': 'Preguntaste sobre síntomas. Intenta preguntar sobre condiciones específicas como "síntomas de COVID-19" o "síntomas de diabetes".',
            'dolor': 'Para preguntas sobre dolor, podrías preguntar sobre áreas específicas o condiciones.',
            'medicamento': 'Para preguntas sobre medicamentos, consulta con un proveedor de atención médica o farmacéutico.',
            'emergencia': 'Para emergencias médicas, llama al 911 inmediatamente.',
            'doctor': 'Para encontrar o reservar citas con doctores, intenta preguntar "¿Cómo puedo reservar una cita con un doctor?"',
            'seguro': 'Para preguntas sobre seguro de salud, intenta preguntar "¿Cómo solicito seguro de salud?"',
            'sangre': 'Para preguntas sobre sangre, intenta preguntar sobre "rango normal de presión arterial" o similar.',
            'corazón': 'Para preocupaciones del corazón, intenta preguntar "¿Qué hacer en caso de un ataque cardíaco?" o consulta a un cardiólogo.',
            'mental': 'Para apoyo de salud mental, intenta preguntar "¿Cómo puedo mejorar mi salud mental?" o contacta a un profesional de salud mental.'
        }
        
        base_response = "No pude encontrar una respuesta específica a tu pregunta en mi base de datos de atención médica. "
        fallback_topics = "Aquí hay algunos temas con los que puedo ayudar:\n\n" + \
                         "• Síntomas e información de COVID-19\n" + \
                         "• Presión arterial y signos vitales\n" + \
                         "• Reservar citas médicas\n" + \
                         "• Aplicaciones de seguro de salud\n" + \
                         "• Procedimientos de emergencia\n" + \
                         "• Consejos de salud mental\n" + \
                         "• Información general de chequeos médicos\n\n" + \
                         "Por favor pregunta sobre cualquiera de estos temas, o consulta con un profesional de la salud para consejos médicos personalizados."
    elif language == 'hi':
        health_topics = {
            'लक्षण': 'आपने लक्षणों के बारे में पूछा। विशिष्ट स्थितियों के बारे में पूछने की कोशिश करें जैसे "कोविड-19 के लक्षण" या "मधुमेह के लक्षण"।',
            'दर्द': 'दर्द संबंधी प्रश्नों के लिए, आप विशिष्ट क्षेत्रों या स्थितियों के बारे में पूछ सकते हैं।',
            'दवा': 'दवा के प्रश्नों के लिए, स्वास्थ्य प्रदाता या फार्मासिस्ट से सलाह लें।',
            'आपातकाल': 'चिकित्सा आपातकाल के लिए, तुरंत 102 पर कॉल करें।',
            'डॉक्टर': 'डॉक्टरों के साथ अपॉइंटमेंट बुक करने के लिए, "मैं डॉक्टर के साथ अपॉइंटमेंट कैसे बुक करूं?" पूछने की कोशिश करें।',
            'बीमा': 'स्वास्थ्य बीमा प्रश्नों के लिए, "मैं स्वास्थ्य बीमा के लिए आवेदन कैसे करूं?" पूछने की कोशिश करें।',
            'रक्त': 'रक्त संबंधी प्रश्नों के लिए, "सामान्य रक्तचाप की सीमा" या इसी तरह के बारे में पूछने की कोशिश करें।',
            'दिल': 'हृदय संबंधी चिंताओं के लिए, "दिल का दौरा पड़ने पर क्या करना चाहिए?" पूछने की कोशिश करें या हृदय रोग विशेषज्ञ से सलाह लें।',
            'मानसिक': 'मानसिक स्वास्थ्य सहायता के लिए, "मैं अपना मानसिक स्वास्थ्य कैसे सुधारूं?" पूछने की कोशिश करें या मानसिक स्वास्थ्य पेशेवर से संपर्क करें।'
        }
        
        base_response = "मुझे अपने स्वास्थ्य डेटाबेस में आपके प्रश्न का विशिष्ट उत्तर नहीं मिला। "
        fallback_topics = "यहाँ कुछ विषय हैं जिनमें मैं मदद कर सकता हूँ:\n\n" + \
                         "• कोविड-19 के लक्षण और जानकारी\n" + \
                         "• रक्तचाप और महत्वपूर्ण संकेत\n" + \
                         "• डॉक्टर की अपॉइंटमेंट बुकिंग\n" + \
                         "• स्वास्थ्य बीमा आवेदन\n" + \
                         "• आपातकालीन प्रक्रियाएं\n" + \
                         "• मानसिक स्वास्थ्य टिप्स\n" + \
                         "• सामान्य स्वास्थ्य जांच की जानकारी\n\n" + \
                         "कृपया इनमें से किसी भी विषय के बारे में पूछें, या व्यक्तिगत चिकित्सा सलाह के लिए स्वास्थ्य पेशेवर से सलाह लें।"
    else:
        health_topics = {
            'symptoms': 'You asked about symptoms. Try asking about specific conditions like "COVID-19 symptoms" or "diabetes symptoms".',
            'pain': 'For pain-related questions, you might want to ask about specific areas or conditions.',
            'medication': 'For medication questions, consult with a healthcare provider or pharmacist.',
            'emergency': 'For medical emergencies, call 911 immediately.',
            'doctor': 'To find or book appointments with doctors, try asking "How can I book an appointment with a doctor?"',
            'insurance': 'For health insurance questions, try asking "How do I apply for health insurance?"',
            'blood': 'For blood-related questions, try asking about "normal blood pressure range" or similar.',
            'heart': 'For heart-related concerns, try asking "What to do in case of a heart attack?" or consult a cardiologist.',
            'mental': 'For mental health support, try asking "How can I improve my mental health?" or contact a mental health professional.'
        }
        
        base_response = "I couldn't find a specific answer to your question in my healthcare database. "
        fallback_topics = "Here are some topics I can help with:\n\n" + \
                         "• COVID-19 symptoms and information\n" + \
                         "• Blood pressure and vital signs\n" + \
                         "• Booking doctor appointments\n" + \
                         "• Health insurance applications\n" + \
                         "• Emergency procedures\n" + \
                         "• Mental health tips\n" + \
                         "• General health checkup information\n\n" + \
                         "Please ask about any of these topics, or consult with a healthcare professional for personalized medical advice."

    suggestions = []
    for keyword in keywords:
        for topic, suggestion in health_topics.items():
            if keyword in topic or topic in keyword:
                suggestions.append(suggestion)
                break

    if suggestions:
        return base_response + " " + suggestions[0] + "\n\nPara preocupaciones médicas específicas, por favor consulta con un profesional de la salud calificado." if language == 'es' else base_response + " " + suggestions[0] + "\n\nFor specific medical concerns, please consult with a qualified healthcare professional."
    else:
        return base_response + fallback_topics

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    user_input = request.json.get('message', '').strip()
    user_id = get_or_create_session()
    
    # Detect language
    detected_language = detect_language(user_input)
    session['language'] = detected_language

    if not user_input:
        empty_response = {
            'en': f'Please ask me a question about healthcare! I\'m {CHATBOT_NAME}, here to help.',
            'es': f'¡Por favor hazme una pregunta sobre atención médica! Soy {CHATBOT_NAME}, aquí para ayudar.',
            'hi': f'कृपया मुझसे स्वास्थ्य के बारे में कोई प्रश्न पूछें! मैं {CHATBOT_NAME} हूं, यहाँ मदद के लिए।'
        }
        return jsonify({
            'response': empty_response[detected_language],
            'confidence': 0,
            'status': 'empty_input',
            'language': detected_language,
            'chatbot_name': CHATBOT_NAME
        })

    # Handle special commands
    if user_input.lower() in ['what can i call you', 'what is your name', 'who are you', '¿cómo te llamas?', '¿quién eres?', 'आपका नाम क्या है', 'आप कौन हैं', 'मैं आपको क्या कह सकता हूं']:
        name_response = {
            'en': f'You can call me {CHATBOT_NAME}! I\'m your AI healthcare assistant. I\'m here to help you with medical questions, health information, and general wellness guidance. Feel free to ask me anything about healthcare!',
            'es': f'¡Puedes llamarme {CHATBOT_NAME}! Soy tu asistente de salud con IA. Estoy aquí para ayudarte con preguntas médicas, información de salud y orientación general de bienestar. ¡Siéntete libre de preguntarme cualquier cosa sobre atención médica!',
            'hi': f'आप मुझे {CHATBOT_NAME} कह सकते हैं! मैं आपका AI स्वास्थ्य सहायक हूं। मैं यहाँ आपकी चिकित्सा प्रश्नों, स्वास्थ्य जानकारी और सामान्य कल्याण मार्गदर्शन में मदद के लिए हूं। स्वास्थ्य के बारे में मुझसे कुछ भी पूछने में संकोच न करें!'
        }
        response = name_response[detected_language]
        save_message_to_history(user_id, user_input, response, detected_language)
        return jsonify({
            'response': response,
            'confidence': 100,
            'status': 'identity',
            'language': detected_language,
            'chatbot_name': CHATBOT_NAME
        })

    # Enhanced similarity search with language support
    global faq_data, faq_questions, faq_answers, vectorizer, tfidf_matrix
    
    # Switch to appropriate language data
    if detected_language == 'es' and multilingual_faq['es']:
        faq_data = multilingual_faq['es']
        faq_questions = [item['question'] for item in faq_data]
        faq_answers = [item['answer'] for item in faq_data]
        vectorizer = setup_language_vectorizer('es')
        if faq_questions:
            processed_questions = [preprocess_text(q) for q in faq_questions]
            tfidf_matrix = vectorizer.fit_transform(processed_questions)
    elif detected_language == 'hi' and multilingual_faq['hi']:
        faq_data = multilingual_faq['hi']
        faq_questions = [item['question'] for item in faq_data]
        faq_answers = [item['answer'] for item in faq_data]
        vectorizer = setup_language_vectorizer('hi')
        if faq_questions:
            processed_questions = [preprocess_text(q) for q in faq_questions]
            tfidf_matrix = vectorizer.fit_transform(processed_questions)
    else:
        faq_data = multilingual_faq['en']
        faq_questions = [item['question'] for item in faq_data]
        faq_answers = [item['answer'] for item in faq_data]

    answer, similarity, confidence_info = enhanced_similarity_search(user_input)

    if answer:
        response = answer
        status = 'matched'
    else:
        response = generate_fallback_response(user_input, detected_language)
        status = 'fallback'

    # Save to chat history
    save_message_to_history(user_id, user_input, response, detected_language)

    return jsonify({
        'response': response,
        'confidence': float(similarity * 100),
        'status': status,
        'debug_info': confidence_info,
        'language': detected_language,
        'chatbot_name': CHATBOT_NAME
    })

@app.route('/chat/history')
def get_chat_history_route():
    """Get chat history for current session"""
    user_id = get_or_create_session()
    history = get_chat_history(user_id)
    return jsonify({
        'history': history,
        'user_id': user_id,
        'total_messages': len(history)
    })

@app.route('/chat/clear', methods=['POST'])
def clear_chat_history():
    """Clear chat history for current session"""
    user_id = get_or_create_session()
    if user_id in chat_histories:
        chat_histories[user_id] = []
    
    clear_response = {
        'en': f'Chat history cleared! I\'m {CHATBOT_NAME}, ready to help you with healthcare questions.',
        'es': f'¡Historial de chat borrado! Soy {CHATBOT_NAME}, listo para ayudarte con preguntas de salud.',
        'hi': f'चैट इतिहास साफ़ कर दिया गया! मैं {CHATBOT_NAME} हूं, स्वास्थ्य प्रश्नों में आपकी मदद के लिए तैयार।'
    }
    language = session.get('language', 'en')
    
    return jsonify({
        'status': 'cleared',
        'message': clear_response[language],
        'chatbot_name': CHATBOT_NAME
    })

@app.route('/language', methods=['POST'])
def set_language():
    """Set user language preference"""
    language = request.json.get('language', 'en')
    if language in ['en', 'es', 'hi']:
        session['language'] = language
        return jsonify({
            'status': 'success',
            'language': language,
            'message': CHATBOT_PERSONALITY[language]
        })
    return jsonify({'status': 'error', 'message': 'Unsupported language'})

@app.route('/health')
def health_check():
    """Health check endpoint for monitoring"""
    return jsonify({
        'status': 'healthy',
        'faq_count': len(faq_data),
        'nlp_model': 'en_core_web_sm' if nlp else 'fallback',
        'version': '3.0',
        'features': ['chat_history', 'bilingual_support', 'personality'],
        'chatbot_name': CHATBOT_NAME,
        'supported_languages': ['en', 'es', 'hi']
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)