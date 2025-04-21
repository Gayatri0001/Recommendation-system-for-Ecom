from flask import Flask, render_template, jsonify, request, redirect, url_for, session, flash
from bson.objectid import ObjectId
from pymongo import MongoClient
from flask_bcrypt import Bcrypt
import os
from werkzeug.utils import secure_filename
from datetime import datetime
import math
import re


app = Flask(__name__, static_url_path='', static_folder='.', template_folder='.')
app.secret_key = '8f0504a81e235e6dbdb386fa0d932bb403ea3d466a2d3156'
bcrypt = Bcrypt(app)

# Connect to MongoDB
client = MongoClient('mongodb://localhost:27017/')
db = client['scholar_ecommerce']
products_collection = db['products']
stores_collection = db['stores']
users_collection = db['users']
wishlist_collection = db['wishlists']
cart_collection = db['carts']
orders_collection = db['orders']


# Route to serve the index.html
@app.route('/')
def index():
    return render_template('index.html')  # Renders index.html from the current folder


# Route for individual product pages
# @app.route('/product/<product_id>')
# def product_page(product_id):
#     product = products_collection.find_one({'_id': ObjectId(product_id)})
#     if product:
#         # Fetching recommended stores based on product category
#         product_category = product.get("Category", "").lower()
#         return render_template('product.html', product=product, product_category=product_category)
#     else:
#         return "Product not found", 404

####################################################################
# offline store recommendations API
# @app.route('/get-stores/<product_id>')
# def get_stores(product_id):
#     product = products_collection.find_one({'_id': ObjectId(product_id)})
#
#     if not product:
#         return jsonify({"error": "Product not found"}), 404
#
#     product_category = product.get("Category", "").lower()
#
#     # Find stores matching the product category
#     stores = list(stores_collection.find({"category": product_category}, {"_id": 0}))
#
#     return jsonify(stores)


def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calculate the great circle distance in kilometers between two points
    on the Earth specified by latitude and longitude using the Haversine formula.
    """
    R = 6371  # Earth radius in kilometers
    dLat = math.radians(lat2 - lat1)
    dLon = math.radians(lon2 - lon1)
    a = math.sin(dLat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dLon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


# def extract_coords(map_url):
#     """
#     Extract latitude and longitude from the map_url.
#     This function looks for a pattern like "@17.6762693,75.327438," in the URL.
#     """
#     match = re.search(r'@([-\d.]+),([-\d.]+),', map_url)
#     if match:
#         try:
#             lat = float(match.group(1))
#             lng = float(match.group(2))
#             return lat, lng
#         except ValueError:
#             return None, None
#     return None, None

def extract_coords(map_url):
    """Extract latitude and longitude from map_url.
       Tries patterns: '@lat,lng,' and '?q=lat,lng'
    """
    pattern = r"@([-.\d]+),([-.\d]+),"
    match = re.search(pattern, map_url)
    if match:
        try:
            return float(match.group(1)), float(match.group(2))
        except ValueError:
            pass
    pattern2 = r"\?q=([-.\d]+),([-.\d]+)"
    match2 = re.search(pattern2, map_url)
    if match2:
        try:
            return float(match2.group(1)), float(match2.group(2))
        except ValueError:
            pass
    return None, None


@app.route('/product/<product_id>')
def product_page(product_id):
    product = products_collection.find_one({'_id': ObjectId(product_id)})
    if product:
        # Render the product page; store recommendations are fetched via API.
        return render_template('product.html', product=product)
    else:
        return "Product not found", 404


# @app.route('/get-stores/<product_id>')
# def get_stores(product_id):
#     product = products_collection.find_one({'_id': ObjectId(product_id)})
#     if not product:
#         return jsonify({'error': 'Product not found'}), 404
#
#     # Optionally get user's coordinates from query parameters.
#     user_lat = request.args.get('user_lat')
#     user_lng = request.args.get('user_lng')
#     if user_lat and user_lng:
#         try:
#             user_lat = float(user_lat)
#             user_lng = float(user_lng)
#         except ValueError:
#             user_lat = user_lng = None
#     else:
#         user_lat = user_lng = None
#
#     # Determine the category for filtering stores.
#     category = ""
#     if product.get('Category'):
#         category = product.get('Category').lower()
#     elif product.get('category'):
#         category = product.get('category').lower()
#
#     recommended_stores = list(stores_collection.find({'category': category}))
#
#     stores_data = []
#     for store in recommended_stores:
#         map_url = store.get('map_url', '#')
#         # Try to get lat/lng from store document; otherwise, extract from map_url.
#         lat = store.get('lat')
#         lng = store.get('lng')
#         if lat is None or lng is None:
#             lat, lng = extract_coords(map_url)
#         store_data = {
#             'storeName': store.get('storeName', 'Unknown'),
#             'location': store.get('location', 'Unknown'),
#             'price': store.get('price', 'N/A'),
#             'map_url': map_url,
#             'lat': lat,
#             'lng': lng,
#             # New fields added:
#             'discount_offer': store.get('discount_offer', 'No discount offer'),
#             'warranty': store.get('warranty', 'Standard warranty'),
#             'guaranty': store.get('guaranty', 'Standard guaranty'),
#             'available_quantity': store.get('available_quantity', 'Not specified'),
#             'recommended_product': product.get('product_name', 'Unknown')
#         }
#         if user_lat is not None and user_lng is not None and lat is not None and lng is not None:
#             distance = haversine_distance(user_lat, user_lng, lat, lng)
#             store_data['distance'] = round(distance, 2)  # in kilometers
#         else:
#             store_data['distance'] = None
#         stores_data.append(store_data)
#
#     # If user's location is available, sort the list by distance.
#     if user_lat is not None and user_lng is not None:
#         stores_data = sorted(stores_data, key=lambda x: x['distance'] if x['distance'] is not None else float('inf'))
#
#     return jsonify({'stores': stores_data})


@app.route('/get-stores/<product_id>')
def get_stores(product_id):
    product = products_collection.find_one({'_id': ObjectId(product_id)})
    if not product:
        return jsonify({"error": "Product not found"}), 404

    # Retrieve product details
    product_name = product.get("product_name", "")
    product_category = (product.get("Category") or product.get("category") or "").lower()

    # Get user's geolocation (optional)
    user_lat = request.args.get('user_lat')
    user_lng = request.args.get('user_lng')
    if user_lat and user_lng:
        try:
            user_lat = float(user_lat)
            user_lng = float(user_lng)
        except ValueError:
            user_lat = user_lng = None
    else:
        user_lat = user_lng = None

    # Query stores that sell **this exact product**
    stores_cursor = stores_collection.find({
        "category": product_category,
        "products_supported.product_name": product_name
    })

    stores_data = []
    for store in stores_cursor:
        map_url = store.get("map_url", "#")
        lat, lng = extract_coords(map_url)

        # Find the exact product details inside products_supported array
        product_entry = next((p for p in store.get("products_supported", []) if p.get("product_name") == product_name), None)
        if not product_entry:
            continue  # Skip if the product is not listed in the store

        store_data = {
            "storeName": store.get("storeName", "Unknown"),
            "location": store.get("location", "Unknown"),
            "price": product_entry.get("price", "N/A"),
            "map_url": map_url,
            "discount_offer": product_entry.get("discount_offer", "No offer"),
            "warranty": product_entry.get("warranty", "Standard warranty"),
            "guaranty": product_entry.get("guaranty", "Standard guaranty"),
            "available_quantity": product_entry.get("available_quantity", "Not specified"),
            "recommended_product": product_name
        }

        # Calculate and add distance if user location is provided
        if user_lat is not None and user_lng is not None and lat is not None and lng is not None:
            distance = haversine_distance(user_lat, user_lng, lat, lng)
            store_data["distance"] = round(distance, 2)
        else:
            store_data["distance"] = None

        stores_data.append(store_data)

    # Sort by distance if user location was provided
    if user_lat is not None and user_lng is not None:
        stores_data = sorted(stores_data, key=lambda x: x["distance"] if x["distance"] is not None else float('inf'))

    if not stores_data:
        return jsonify({"stores": [], "message": "No offline stores found for this product."})
    return jsonify({"stores": stores_data})


# Route for individual product pagesm
# @app.route('/product/<product_id>')
# def product_page(product_id):
#     product = products_collection.find_one({'_id': ObjectId(product_id)})
#
#     if product:
#         # Fetching recommended stores based on product category
#         recommended_stores = list(stores_collection.find({'category': product.get('Category', '').lower()}))
#         return render_template('product.html', product=product, recommended_stores=recommended_stores)
#     else:
#         return "Product not found", 404


# API Route to get store recommendations
# @app.route('/get-stores/<product_id>')
# def get_stores(product_id):
#     product = products_collection.find_one({'_id': ObjectId(product_id)})
#
#     if not product:
#         return jsonify({'error': 'Product not found'}), 404
#
#     # Fetch stores based on product category
#     recommended_stores = list(stores_collection.find({'category': product.get('Category', '').lower()}))
#
#     stores_data = [{
#         'storeName': store.get('storeName', 'Unknown'),
#         'location': store.get('location', 'Unknown'),
#         'price': store.get('price', 'N/A'),
#         'map_url': store.get('map_url', '#')
#     } for store in recommended_stores]
#
#     return jsonify({'stores': stores_data})


# API endpoint to serve the best-selling products
@app.route('/api/best-selling-products', methods=['GET'])
def get_best_selling_products():
    products = products_collection.find({})
    product_list = []
    for product in products:
        product_list.append({
            "_id": str(product['_id']),  # Convert ObjectId to string for the frontend
            "product_name": product['product_name'],
            "price": product['price'],
            "discount": product['discount'],
            "rating": product['rating'],
            "reviews": product['reviews'],
            "image_url": product['image_url'],
        })
    return jsonify(product_list)


@app.route('/best-selling-products')
def best_selling_products_page():
    # Query the database for best-selling products
    best_selling_products = products_collection.find({"category": "best_selling"})

    product_list = []
    for product in best_selling_products:
        product_list.append({
            "_id": str(product['_id']),
            "product_name": product['product_name'],
            "price": product['price'],
            "discount": product['discount'],
            "rating": product['rating'],
            "reviews": product['reviews'],
            "image_url": product['image_url'],
        })

    # Render the best-selling products page
    return render_template('best_selling_products.html', products=product_list)


# API to fetch featured products
@app.route('/api/featured-products', methods=['GET'])
def get_featured_products():
    # Assuming you have a 'featured' field to identify featured products
    featured_products = products_collection.find({'featured': True})
    featured_list = []
    for product in featured_products:
        featured_list.append({
            "_id": str(product['_id']),  # Convert ObjectId to string for frontend
            "product_name": product['product_name'],
            "price": product['price'],
            "discount": product['discount'],
            "rating": product['rating'],
            "reviews": product['reviews'],
            "image_url": product['image_url'],
        })
    return jsonify(featured_list)


# API to fetch popular products
@app.route('/api/popular-products', methods=['GET'])
def get_popular_products():
    # Assuming you have a 'popular' field to identify popular products
    popular_products = products_collection.find({'popular': True})
    popular_list = []
    for product in popular_products:
        popular_list.append({
            "_id": str(product['_id']),  # Convert ObjectId to string for frontend
            "product_name": product['product_name'],
            "price": product['price'],
            "discount": product['discount'],
            "rating": product['rating'],
            "reviews": product['reviews'],
            "image_url": product['image_url'],
        })
    return jsonify(popular_list)


# Route to render recommendations page
@app.route('/recommendations', methods=['GET'])
def recommendations():
    return render_template('recommendations.html')


# API endpoint to get recommendations based on user filters
@app.route('/get-recommendations', methods=['POST'])
def get_recommendations():
    data = request.json
    product_name = data.get('productName', '')
    location = data.get('location', '')
    category = data.get('category', '')
    min_price = int(data.get('minPrice', 0))
    max_price = int(data.get('maxPrice', 10000))

    # Query MongoDB for stores that match the criteria
    query = {
        # 'product_name': {'$regex': product_name, '$options': 'i'},  # Case insensitive search
        'location': {"$regex": location, "$options": "i"},
        'category': category,
        'price': {'$gte': min_price, '$lte': max_price}
    }

    # Query MongoDB
    store_recommendations = list(stores_collection.find(query))

    # Print query and recommendations to debug
    print("Query:", query)
    print("Store Recommendations:", store_recommendations)

    # stores = stores_collection.find(query)

    # Format the data to return
    recommendations = []
    for store in store_recommendations:
        recommendations.append({
            "storeName": store['storeName'],
            "location": store['location'],
            "price": store['price'],
            "category": store['category']
        })

    return jsonify(recommendations)


# Signup route
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        # Check if user already exists
        if users_collection.find_one({'email': email}):
            return 'User already exists!'

        # Hash the password and store it
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        users_collection.insert_one({'username': username, 'email': email, 'password': hashed_password})

        return redirect(url_for('login'))

    return render_template('signup.html')


# Login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        # Check if the user exists
        user = users_collection.find_one({'email': email})

        if user and bcrypt.check_password_hash(user['password'], password):
            session['username'] = user['username']  # Save user session
            session['user_id'] = str(user['_id'])  # Store user_id in session
            return redirect(url_for('index'))

        return 'Invalid credentials, please try again.'

    return render_template('login.html')


# Logout route
@app.route('/logout')
def logout():
    session.clear()  # Clear all session data
    session.pop('username', None)  # Remove user session
    return redirect(url_for('index'))


# Route to check if user is logged in (for navbar display)
@app.route('/is_logged_in')
def is_logged_in():
    return jsonify({'logged_in': 'username' in session, 'username': session.get('username')})


# Route for wishlist functionality
@app.route('/add-to-wishlist', methods=['POST'])
def add_to_wishlist():
    if 'username' not in session:
        return jsonify({'message': 'Please login to add items to wishlist.'}), 403

    data = request.json
    product_id = data['productId']

    # Find the product
    product = products_collection.find_one({'_id': ObjectId(product_id)})

    if not product:
        return jsonify({'message': 'Product not found.'}), 404

    # Add product to user's wishlist
    wishlist_collection.update_one(
        {'username': session['username']},
        {'$addToSet': {'products': product_id}},
        upsert=True
    )

    return jsonify({'message': 'Product added to wishlist.'})


# Route for add to cart functionality
@app.route('/add-to-cart', methods=['POST'])
def add_to_cart():
    if 'username' not in session:
        return jsonify({'message': 'Please login to add items to cart.'}), 403

    data = request.json
    product_id = data['productId']

    # Find the product
    product = products_collection.find_one({'_id': ObjectId(product_id)})

    if not product:
        return jsonify({'message': 'Product not found.'}), 404

    # Add product to user's cart
    cart_collection.update_one(
        {'username': session['username']},
        {'$addToSet': {'products': product_id}},
        upsert=True
    )

    return jsonify({'message': 'Product added to cart.'})


# # Route to checkout(Buy Now) Page
# @app.route('/checkout', methods=['GET'])
# def checkout():
#     if 'user_id' not in session:
#         # If user is not logged in, redirect them to the login page
#         return redirect(url_for('login'))
#
#     product_ids = request.args.get('product_ids')  # Get product IDs from query string (from cart or Buy Now)
#
#     if not product_ids:
#         return "No products selected", 400
#
#     # Retrieve products by their ObjectIds
#     product_ids = product_ids.split(',')
#     products = []
#     total_price = 0
#
#     for pid in product_ids:
#         product = products_collection.find_one({'_id': ObjectId(pid)})
#         if product:
#             # Calculate price after discount if applicable
#             final_price = product['price'] - (product['price'] * product['discount'] / 100)
#             total_price += final_price
#             products.append({
#                 'product_name': product['product_name'],
#                 'price': product['price'],
#                 'discount': product['discount'],
#                 'final_price': final_price,
#                 'image_url': product['image_url'],
#                 'rating': product['rating']
#             })
#         else:
#             return "Product not found", 404
#
#     user = users_collection.find_one({'_id': ObjectId(session['user_id'])})
#
#     return render_template('checkout.html', products=products, total_price=total_price, user=user)


# Render to wishlist page
@app.route('/wishlist')
def wishlist():
    if 'username' not in session:
        return redirect(url_for('login'))

    # Find the user's wishlist
    wishlist = wishlist_collection.find_one({'username': session['username']})

    # Get the list of product IDs from the cart
    product_ids = wishlist['products'] if wishlist else []

    # Retrieve product details for the product IDs in the cart
    products = products_collection.find({'_id': {'$in': [ObjectId(pid) for pid in product_ids]}})

    return render_template('wishlist.html', products=products)


# Render to cart page
@app.route('/cart')
def cart():
    if 'username' not in session:
        return redirect(url_for('login'))

    # Fetch user from session
    user = users_collection.find_one({'username': session.get('username')})

    # Find the user's cart
    cart = cart_collection.find_one({'username': user['username']})

    cart_products = [
        products_collection.find_one({'_id': ObjectId(product_id)})
        for product_id in cart['products']
    ] if cart else []

    total_price = 0
    total_discount = 0
    total_delivery_charges = 0
    secured_packaging_fee = 59  # Fixed charge

    # session['cart_products'] = [
    #     {
    #         'product_id': str(product['_id']),
    #         'product_name': product['product_name'],
    #         'price': product['price'],
    #         'discount': product['discount'],
    #     }
    #     for product in cart_products
    # ]

    # Calculate total values for price, discount, delivery
    for product in cart_products:
        discount_amount = (product['price'] * product['discount']) / 100
        final_price = product['price'] - discount_amount
        product['final_price'] = final_price

        total_price += product['price']
        total_discount += discount_amount
        total_delivery_charges += product.get('delivery_charges', 0)  # Default to 0 if not present

    final_amount = total_price - total_discount + total_delivery_charges + secured_packaging_fee
    total_savings = total_discount + total_delivery_charges  # User saves on discount and free delivery

    # session['cart_products'] = [
    #     {
    #         'product_id': str(product['_id']),
    #         'product_name': product['product_name'],
    #         'price': product['price'],
    #         'discount': product['discount'],
    #     }
    #     for product in cart_products
    # ]

    # return render_template('cart.html', products=cart_products)
    return render_template('cart.html', products=cart_products, total_price=total_price,
                           total_discount=total_discount, total_delivery_charges=total_delivery_charges,
                           final_amount=final_amount, total_savings=total_savings)


# Route to remove item from cart
@app.route('/remove-from-cart', methods=['POST'])
def remove_from_cart():
    if 'username' in session:
        # Get the logged-in user's username
        username = session['username']

        # Get product ID from the form
        product_id = request.form.get('product_id')

        # Use $pull to remove the product from the user's cart
        cart_collection.update_one(
            {'username': username},
            {'$pull': {'products': product_id}}  # Remove the specific product ID from products array
        )

        # Redirect back to the cart page after removing the product
        return redirect(url_for('cart'))
    else:
        # If the user is not logged in, redirect to login page
        return redirect(url_for('login'))


# Route to remove item from wishlist
@app.route('/remove-from-wishlist', methods=['POST'])
def remove_from_wishlist():
    if 'username' in session:
        # Get the logged-in user's username
        username = session['username']

        # Get product ID from the form
        product_id = request.form.get('product_id')

        # Use $pull to remove the product from the user's wishlist
        wishlist_collection.update_one(
            {'username': username},
            {'$pull': {'products': product_id}}  # Remove the specific product ID from products array
        )

        # Redirect back to the wishlist page after removing the product
        return redirect(url_for('wishlist'))
    else:
        # If the user is not logged in, redirect to login page
        return redirect(url_for('login'))


# Route for category
@app.route('/category/<category_name>')
def category(category_name):
    # Normalize category_name to lowercase as per your product data
    category_name = category_name.lower()

    # Find products that match the selected category
    products_cursor = products_collection.find({'Category': category_name})

    # Convert cursor to a list
    products = list(products_cursor)

    # Pass the category name and products to the template
    return render_template('category.html', products=products, category_name=category_name)


# Route for user profile
@app.route('/profile')
def profile():
    if 'username' not in session:
        return redirect(url_for('login'))

    # Fetch user details from MongoDB
    user = users_collection.find_one({'username': session['username']})

    if not user:
        return "User not found", 404

    return render_template('profile.html', user=user)


# Update profile route
@app.route('/update-profile', methods=['POST'])
def update_profile():
    if 'username' not in session:
        return redirect(url_for('login'))

    # Initialize an empty dictionary for updates
    update_data = {}

    # Get data from form
    email = request.form.get('email')
    phone = request.form.get('phone')
    address_line = request.form.get('address_line')
    city = request.form.get('city')
    state = request.form.get('state')
    postal_code = request.form.get('postal_code')
    profile_image = request.form.get('profile_image')

    # Only add to update_data if the field is not empty
    if email:
        update_data['email'] = email
    if phone:
        update_data['phone'] = phone
    if address_line and city and state and postal_code:
        new_address = {
            'address_line': address_line,
            'city': city,
            'state': state,
            'postal_code': postal_code,
            'phone': phone
        }
        users_collection.update_one(
            {'username': session['username']},
            {'$push': {'addresses': new_address}}
        )
    if profile_image:
        update_data['profile_image'] = profile_image

    # Update user details in the database
    users_collection.update_one(
        {'username': session['username']},
        {'$set': update_data}
    )

    return redirect(url_for('profile'))


# Define a folder to store uploaded profile images
UPLOAD_FOLDER = 'images/profile_images'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# route to upload image in profile
@app.route('/upload-profile-image', methods=['POST'])
def upload_profile_image():
    if 'username' not in session:
        return jsonify({'message': 'Please login to upload your profile image.'}), 403

    if 'profile_image' not in request.files:
        return jsonify({'message': 'No file part'}), 400

    file = request.files['profile_image']

    if file.filename == '':
        return jsonify({'message': 'No selected file'}), 400

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        # Update the user's profile image URL in the database
        image_url = f'/images/profile_images/{filename}'
        users_collection.update_one(
            {'username': session['username']},
            {'$set': {'profile_image': image_url}}
        )

        return jsonify({'new_image_url': image_url})
    else:
        return jsonify({'message': 'File not allowed'}), 400


# Route for search functionality
@app.route('/search_results', methods=['GET'])
def search():
    search_query = request.args.get('query', '').strip()

    if not search_query:
        return render_template('search_results.html', products=[], query=search_query)

    # MongoDB search query using regular expression for case-insensitive and partial match
    search_pattern = {'$regex': search_query, '$options': 'i'}  # 'i' for case-insensitivity

    # Searching products based on product name, category, or description fields
    products = products_collection.find({
        '$or': [
            {'product_name': search_pattern},
            {'Category': search_pattern}
            # Assuming you have a 'description' field in your products
            # {'description': search_pattern}
        ]
    })

    # Convert the cursor to a list for easier processing
    products_list = list(products)

    return render_template('search_results.html', products=products_list, query=search_query)


# route for live search
@app.route('/live_search', methods=['GET'])
def live_search():
    search_query = request.args.get('query', '').strip()
    print(f"Search query: {search_query}")  # Debugging: log the query in the console

    if not search_query:
        return jsonify([])

    # Use regular expression for partial matching (case-insensitive)
    search_pattern = {'$regex': search_query, '$options': 'i'}

    # Fetch products matching the query
    products = products_collection.find({
        '$or': [
            {'product_name': search_pattern},
            {'Category': search_pattern}
            # If you have a description field
            # {'description': search_pattern}
        ]
    }).limit(5)  # Limit suggestions to top 5 results

    # Extract product names and return them as suggestions
    suggestions = [{"product_name": product["product_name"], "id": str(product["_id"])} for product in products]

    return jsonify(suggestions)


@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    # Fetch the logged-in user
    user = users_collection.find_one({'username': session.get('username')})
    cart_products = session.get('cart_products', [])

    # Fetch user’s saved addresses
    user_addresses = user.get('addresses', [])

    # Handle GET Request (display checkout page)
    if request.method == 'GET':
        # Handle Cart Checkout: If coming from the cart
        if 'cart' in request.args or session.get('cart_products'):
            # Fetch products from the session
            cart_products = session.get('cart_products', [])

        # Handle Buy Now: If product_id is passed in query string
        if 'product_id' in request.args:
            product_id = request.args.get('product_id')
            product = products_collection.find_one({'_id': ObjectId(product_id)})
            cart_products.append({
                    'product_id': str(product['_id']),
                    'product_name': product['product_name'],
                    'price': product['price'],
                    'discount': product['discount'],
                })
                # Store the products in session for use in POST request
            session['cart_products'] = cart_products

        # Calculate total price for the checkout
        total_price = sum([product['price'] * (1 - product['discount'] / 100) for product in cart_products])

    # Handle POST Request (place the order)
    if request.method == 'POST' and 'checkout' in request.form:
        # Get the selected address (from the radio button)
        selected_address = request.form.get('selected_address')

        # If the user selected an existing address
        if selected_address != 'new':
            address = selected_address
        else:
            # Collect new address from form
            new_address = {
                'address_line': request.form.get('address_line'),
                'city': request.form.get('city'),
                'state': request.form.get('state'),
                'postal_code': request.form.get('postal_code'),
                'phone': request.form.get('new_phone')
            }
            # Add new address to user's addresses array in MongoDB
            users_collection.update_one(
                {'_id': user['_id']},
                {'$push': {'addresses': new_address}}
            )
            address = new_address  # Use this new address for the order

        # Retrieve product details from session
        cart_products = session.get('cart_products', [])

        if not cart_products:
            flash("Cart is empty.")
            return redirect(url_for('checkout'))

        # Calculate total price again for security
        total_price = sum([product['price'] * (1 - product['discount'] / 100) for product in cart_products])

        # Insert the order into the database
        order_data = {
            'user_id': user['_id'],
            'products': cart_products,
            'total_price': total_price,
            'address': address,
            'phone': request.form.get('phone'),
            'order_date': datetime.now(),
            'status': 'Confirmed'
        }
        orders_collection.insert_one(order_data)

        # Remove the items from the cart after placing the order
        cart_collection.update_one(
            {'username': user['username']},
            {'$set': {'products': []}}  # Clear the cart
        )

        # Clear cart after placing the order
        session.pop('cart_products', None)

        print("Order inserted successfully:", order_data)
        return redirect(url_for('order_confirmation'))

    # Calculate total price for rendering checkout page (GET request)
    total_price = sum([product['price'] * (1 - product['discount'] / 100) for product in cart_products])

    # Render checkout page with user, products, and total price
    return render_template('checkout.html', products=cart_products, total_price=total_price, user=user)


@app.route('/place_order', methods=['POST'])
def place_order():
    user = users_collection.find_one({'username': session.get('username')})
    cart_products = session.get('cart_products', [])

    # Recalculate total price
    total_price = sum([product['price'] * (1 - product['discount'] / 100) for product in cart_products])

    # Insert order in database
    order_data = {
        'user_id': user['_id'],
        'products': cart_products,
        'total_price': total_price,
        'order_date': datetime.now(),
        'status': 'Confirmed'
    }
    orders_collection.insert_one(order_data)

    # Clear the cart
    session.pop('cart_products', None)

    # Remove the items from the cart after placing the order
    # cart_collection.update_one(
    #     {'username': user['username']},
    #     {'$set': {'products': []}}  # Clear the cart
    # )

    return redirect(url_for('order_confirmation'))


@app.route('/order_confirmation')
def order_confirmation():
    # Fetch user from session
    user = users_collection.find_one({'username': session.get('username')})

    # Fetch the latest order of the user
    order = orders_collection.find_one({'user_id': user['_id']}, sort=[('order_date', -1)])

    return render_template('order_confirmation.html', order=order)


if __name__ == "__main__":
    app.secret_key = '8f0504a81e235e6dbdb386fa0d932bb403ea3d466a2d3156'
    app.run(debug=True)


