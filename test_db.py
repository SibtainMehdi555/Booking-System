from app import app, db, User, Booking
from datetime import datetime

def test_database():
    with app.app_context():
        try:
            # Test User table
            print("\nTesting User table...")
            users = User.query.all()
            print(f"Total users in database: {len(users)}")
            for user in users:
                print(f"User: {user.name}, Email: {user.email}, Created: {user.created_at}")

            # Test Booking table
            print("\nTesting Booking table...")
            bookings = Booking.query.all()
            print(f"Total bookings in database: {len(bookings)}")
            for booking in bookings:
                print(f"Booking: Area={booking.area_name}, Start={booking.start_date}, "
                      f"End={booking.end_date}, People={booking.people}, "
                      f"Cost=${booking.total_cost}, Status={booking.status}")

            # Test database relationships
            print("\nTesting database relationships...")
            for user in users:
                user_bookings = Booking.query.filter_by(user_id=user.id).all()
                print(f"\nUser {user.name}'s bookings:")
                for booking in user_bookings:
                    print(f"- {booking.area_name} ({booking.start_date} to {booking.end_date})")

            print("\nDatabase test completed successfully!")
            return True

        except Exception as e:
            print(f"\nError testing database: {str(e)}")
            return False

if __name__ == "__main__":
    test_database() 