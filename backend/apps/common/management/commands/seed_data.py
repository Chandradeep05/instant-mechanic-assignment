import random
from datetime import timedelta
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction

from apps.customers.models import Customer, Vehicle
from apps.mechanics.models import Mechanic
from apps.bookings.models import ServiceCategory, Booking, BookingStatusHistory

class Command(BaseCommand):
    help = (
        'Seeds the database with realistic demo data and attention scenarios.\n\n'
        'By default, this command is IDEMPOTENT: if data already exists, it exits safely.\n'
        'Use --reset to explicitly wipe all data before reseeding (destructive!).\n\n'
        'Examples:\n'
        '  python manage.py seed_data          # Safe: skips if data exists\n'
        '  python manage.py seed_data --reset  # Destructive: wipes and recreates everything\n'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='DESTRUCTIVE: Wipe all existing data before seeding. Requires explicit flag.',
        )

    def handle(self, *args, **options):
        from apps.bookings.models import Booking
        reset = options.get('reset', False)

        if not reset and Booking.objects.exists():
            self.stdout.write(
                self.style.WARNING(
                    f"Database already contains {Booking.objects.count()} bookings. "
                    "Skipping seed to preserve existing data.\n"
                    "Run with --reset to wipe and reseed: python manage.py seed_data --reset"
                )
            )
            return

        if reset:
            self.stdout.write(
                self.style.WARNING("--reset flag detected. Wiping all data before reseeding...")
            )

        self.stdout.write("Starting database seeding...")

        with transaction.atomic():
            if reset:
                self.clear_data()
            services = self.create_services()
            mechanics = self.create_mechanics()
            customers, vehicles = self.create_customers_and_vehicles()
            self.create_historical_bookings(customers, vehicles, mechanics, services)
            self.create_live_attention_scenarios(customers, vehicles, mechanics, services)

        self.stdout.write(self.style.SUCCESS("Database seeding completed successfully!"))

    def clear_data(self):
        self.stdout.write("Clearing existing data...")
        BookingStatusHistory.objects.all().delete()
        Booking.objects.all().delete()
        Vehicle.objects.all().delete()
        Customer.objects.all().delete()
        Mechanic.objects.all().delete()
        ServiceCategory.objects.all().delete()

    def create_services(self):
        # Realistic Indian market pricing (Delhi NCR / metro city mobile mechanic rates)
        services_data = [
            ("Engine Diagnostic & Scan", "Full OBD-II scan, sensor diagnostics, and code analysis", Decimal("2500.00")),
            ("Full Synthetic Oil & Filter Service", "Premium synthetic oil replacement, OEM oil filter, fluid top-off", Decimal("1800.00")),
            ("Brake Pad & Rotor Replacement", "Front/rear ceramic brake pads and rotor inspection/replacement", Decimal("5500.00")),
            ("Battery Replacement & Test", "High-capacity AGM battery install with terminal cleaning and charging test", Decimal("4500.00")),
            ("Transmission Fluid Flush", "Complete fluid extraction, transmission filter change, and inspection", Decimal("3500.00")),
            ("Suspension & Strut Repair", "Shock absorber, strut replacement, and bushing alignment", Decimal("8500.00")),
            ("A/C Refrigerant Recharge & Leak Test", "R-134a refrigerant vacuum recharge and electronic leak detection", Decimal("3000.00")),
            ("Comprehensive Safety Inspection", "50-point bumper-to-bumper vehicle safety check and road test", Decimal("1500.00")),
        ]
        services = []
        for name, desc, price in services_data:
            s = ServiceCategory.objects.create(name=name, description=desc, base_price=price)
            services.append(s)
        self.stdout.write(f"Created {len(services)} service categories.")
        return services

    def create_mechanics(self):
        # Indian names reflecting realistic fleet diversity
        names = [
            "Rajesh Kumar", "Priya Sharma", "Amit Verma", "Sunita Nair",
            "Vikram Singh", "Anita Patel", "Deepak Gupta", "Kavya Reddy",
            "Suresh Iyer", "Pooja Mehta", "Arun Chauhan", "Meera Joshi",
            "Ravi Tiwari", "Divya Pillai", "Arjun Malhotra", "Neha Saxena",
            "Sandeep Yadav", "Lakshmi Menon", "Rohit Bose", "Ananya Kapoor",
            "Kiran Negi", "Sanjay Dubey", "Pallavi Chandra", "Manoj Pandey", "Geeta Rathi"
        ]

        mechanics = []
        for i, name in enumerate(names):
            if i == len(names) - 1:
                avail = Mechanic.AVAILABILITY_OFFLINE
            elif i == len(names) - 2:
                avail = Mechanic.AVAILABILITY_BREAK
            else:
                avail = Mechanic.AVAILABILITY_AVAILABLE

            rating = Decimal(str(round(random.uniform(4.50, 5.00), 2)))
            # Indian mobile numbers: +91 followed by 10-digit number starting with 6-9
            prefix = random.choice(['6', '7', '8', '9'])
            phone = f"+91 {prefix}{random.randint(100000000, 999999999)}"
            m = Mechanic.objects.create(
                name=name,
                phone=phone,
                availability_status=avail,
                rating=rating
            )
            mechanics.append(m)
        self.stdout.write(f"Created {len(mechanics)} mechanics.")
        return mechanics

    def create_customers_and_vehicles(self):
        # Indian first names and last names
        first_names = [
            "Aarav", "Vivaan", "Aditya", "Vihaan", "Arjun", "Sai", "Reyansh", "Ayaan", "Krishna", "Ishaan",
            "Ananya", "Diya", "Saanvi", "Myra", "Riya", "Priya", "Ishita", "Anika", "Kavya", "Avni",
            "Rohan", "Nikhil", "Karan", "Rahul", "Varun", "Sameer", "Akash", "Siddharth", "Deepak", "Harish",
            "Neha", "Pooja", "Sneha", "Divya", "Megha", "Swati", "Rekha", "Sunita", "Geeta", "Pallavi",
            "Rajesh", "Suresh", "Mahesh", "Ramesh", "Dinesh", "Ganesh", "Lokesh", "Mukesh", "Naresh", "Paresh"
        ]
        last_names = [
            "Sharma", "Verma", "Gupta", "Singh", "Kumar", "Patel", "Mehta", "Joshi", "Nair", "Reddy",
            "Iyer", "Pillai", "Chauhan", "Malhotra", "Saxena", "Yadav", "Tiwari", "Bose", "Kapoor", "Dubey",
            "Chandra", "Pandey", "Rathi", "Menon", "Negi", "Srivastava", "Mishra", "Agarwal", "Jain", "Shah"
        ]

        # Popular car makes in India
        makes_models = [
            ("Maruti Suzuki", "Swift", "HATCHBACK"), ("Maruti Suzuki", "Dzire", "SEDAN"),
            ("Maruti Suzuki", "Brezza", "SUV"), ("Hyundai", "i20", "HATCHBACK"),
            ("Hyundai", "Creta", "SUV"), ("Hyundai", "Verna", "SEDAN"),
            ("Tata", "Nexon", "SUV"), ("Tata", "Harrier", "SUV"),
            ("Mahindra", "Scorpio-N", "SUV"), ("Mahindra", "XUV700", "SUV"),
            ("Honda", "City", "SEDAN"), ("Honda", "Amaze", "SEDAN"),
            ("Toyota", "Innova Crysta", "SUV"), ("Toyota", "Fortuner", "SUV"),
            ("Kia", "Seltos", "SUV"), ("Kia", "Sonet", "SUV"),
            ("Renault", "Kwid", "HATCHBACK"), ("Volkswagen", "Polo", "HATCHBACK"),
            ("Royal Enfield", "Classic 350", "MOTORCYCLE"), ("Hero", "Splendor", "MOTORCYCLE"),
        ]

        # Indian state codes for vehicle registration
        state_codes = ["DL", "MH", "KA", "TN", "UP", "RJ", "GJ", "HR", "WB", "MP", "PB", "AP"]

        now = timezone.now()
        customers = []
        vehicles = []

        for i in range(60):
            fn = random.choice(first_names)
            ln = random.choice(last_names)
            name = f"{fn} {ln}"
            # Indian mobile number
            prefix = random.choice(['6', '7', '8', '9'])
            phone = f"+91 {prefix}{random.randint(100000000, 999999999)}"
            email = f"{fn.lower()}.{ln.lower()}{random.randint(10, 99)}@gmail.com"
            days_ago = random.randint(0, 45)
            created_at = now - timedelta(days=days_ago, hours=random.randint(0, 23), minutes=random.randint(0, 59))

            c = Customer.objects.create(name=name, phone=phone, email=email)
            Customer.objects.filter(id=c.id).update(created_at=created_at)
            c.refresh_from_db()
            customers.append(c)

            num_vehicles = 2 if random.random() < 0.35 else 1
            for _ in range(num_vehicles):
                make, model, vtype = random.choice(makes_models)
                state = random.choice(state_codes)
                # Indian vehicle registration format: DL-01-AB-1234
                district = random.randint(1, 99)
                series = f"{random.choice('ABCDEFGHJKLMNPRSTUVWXYZ')}{random.choice('ABCDEFGHJKLMNPRSTUVWXYZ')}"
                number = random.randint(1000, 9999)
                reg = f"{state}-{district:02d}-{series}-{number}"
                v = Vehicle.objects.create(
                    customer=c,
                    make=make,
                    model=model,
                    registration_number=reg,
                    vehicle_type=vtype
                )
                vehicles.append(v)

        self.stdout.write(f"Created {len(customers)} customers and {len(vehicles)} vehicles.")
        return customers, vehicles

    def create_historical_bookings(self, customers, vehicles, mechanics, services):
        now = timezone.now()
        total_historical = 750
        bookings_created = 0

        self.stdout.write(f"Generating {total_historical} historical bookings over the past 30 days...")

        # We will distribute across 30 days
        for i in range(total_historical):
            days_ago = random.randint(0, 29)
            hour = random.randint(6, 21)
            minute = random.randint(0, 59)
            created_at = (now - timedelta(days=days_ago)).replace(hour=hour, minute=minute, second=0, microsecond=0)

            customer = random.choice(customers)
            cust_vehicles = [v for v in vehicles if v.customer_id == customer.id]
            vehicle = random.choice(cust_vehicles) if cust_vehicles else random.choice(vehicles)
            service = random.choice(services)
            mechanic = random.choice([m for m in mechanics if m.availability_status != Mechanic.AVAILABILITY_OFFLINE])

            # Random price variation (+/- 15%)
            price_mult = Decimal(str(round(random.uniform(0.90, 1.25), 2)))
            amount = round(service.base_price * price_mult, 2)

            # Determine final status for historical
            # If older than 1 day: ~90% completed, ~8% cancelled, ~2% edge
            # If today: mixture of completed, in-progress, arrived, on the way, assigned, pending
            if days_ago > 0:
                rand_val = random.random()
                if rand_val < 0.88:
                    target_status = Booking.STATUS_COMPLETED
                elif rand_val < 0.96:
                    target_status = Booking.STATUS_CANCELLED
                else:
                    target_status = Booking.STATUS_COMPLETED
            else:
                # Today's bookings
                rand_val = random.random()
                if rand_val < 0.45:
                    target_status = Booking.STATUS_COMPLETED
                elif rand_val < 0.60:
                    target_status = Booking.STATUS_IN_PROGRESS
                elif rand_val < 0.75:
                    target_status = Booking.STATUS_ARRIVED
                elif rand_val < 0.85:
                    target_status = Booking.STATUS_ON_THE_WAY
                elif rand_val < 0.93:
                    target_status = Booking.STATUS_ASSIGNED
                elif rand_val < 0.97:
                    target_status = Booking.STATUS_PENDING
                else:
                    target_status = Booking.STATUS_CANCELLED

            booking_num = f"BK-{1000 + i + 1}"

            # Chronological timestamps
            assigned_at = None
            started_at = None
            estimated_arrival_at = None
            arrived_at = None
            completed_at = None
            cancelled_at = None

            if target_status == Booking.STATUS_PENDING:
                mechanic = None
            else:
                assigned_at = created_at + timedelta(minutes=random.randint(3, 15))

            if target_status in [Booking.STATUS_ON_THE_WAY, Booking.STATUS_ARRIVED, Booking.STATUS_IN_PROGRESS, Booking.STATUS_COMPLETED]:
                started_at = assigned_at + timedelta(minutes=random.randint(2, 8))
                estimated_arrival_at = started_at + timedelta(minutes=random.randint(15, 25))

            if target_status in [Booking.STATUS_ARRIVED, Booking.STATUS_IN_PROGRESS, Booking.STATUS_COMPLETED]:
                arrived_at = estimated_arrival_at + timedelta(minutes=random.randint(-3, 6))

            if target_status == Booking.STATUS_COMPLETED:
                completed_at = arrived_at + timedelta(minutes=random.randint(25, 60))

            if target_status == Booking.STATUS_CANCELLED:
                cancelled_at = created_at + timedelta(minutes=random.randint(5, 30))

            b = Booking.objects.create(
                booking_number=booking_num,
                customer=customer,
                vehicle=vehicle,
                mechanic=mechanic,
                service_category=service,
                status=target_status,
                amount=amount,
                is_demo_scenario=False,
                assigned_at=assigned_at,
                started_at=started_at,
                estimated_arrival_at=estimated_arrival_at,
                arrived_at=arrived_at,
                completed_at=completed_at,
                cancelled_at=cancelled_at,
            )
            # Update auto_now_add created_at
            Booking.objects.filter(id=b.id).update(created_at=created_at)

            # Generate chronological status history rows
            history_rows = [
                BookingStatusHistory(
                    booking=b,
                    previous_status="CREATED",
                    new_status=Booking.STATUS_PENDING,
                    changed_at=created_at,
                    changed_by="CUSTOMER",
                    notes="Booking placed via app"
                )
            ]

            if assigned_at:
                history_rows.append(
                    BookingStatusHistory(
                        booking=b,
                        previous_status=Booking.STATUS_PENDING,
                        new_status=Booking.STATUS_ASSIGNED,
                        changed_at=assigned_at,
                        changed_by="DISPATCH_AUTO",
                        notes=f"Assigned to {mechanic.name}"
                    )
                )

            if started_at:
                history_rows.append(
                    BookingStatusHistory(
                        booking=b,
                        previous_status=Booking.STATUS_ASSIGNED,
                        new_status=Booking.STATUS_ON_THE_WAY,
                        changed_at=started_at,
                        changed_by="MECHANIC",
                        notes="Mechanic departed for location"
                    )
                )

            if arrived_at:
                history_rows.append(
                    BookingStatusHistory(
                        booking=b,
                        previous_status=Booking.STATUS_ON_THE_WAY,
                        new_status=Booking.STATUS_ARRIVED,
                        changed_at=arrived_at,
                        changed_by="MECHANIC",
                        notes="Arrived at customer vehicle location"
                    )
                )

            if target_status == Booking.STATUS_IN_PROGRESS:
                in_prog_at = arrived_at + timedelta(minutes=5)
                history_rows.append(
                    BookingStatusHistory(
                        booking=b,
                        previous_status=Booking.STATUS_ARRIVED,
                        new_status=Booking.STATUS_IN_PROGRESS,
                        changed_at=in_prog_at,
                        changed_by="MECHANIC",
                        notes="Commenced diagnostic and repair"
                    )
                )

            if completed_at:
                in_prog_at = arrived_at + timedelta(minutes=5)
                history_rows.append(
                    BookingStatusHistory(
                        booking=b,
                        previous_status=Booking.STATUS_ARRIVED,
                        new_status=Booking.STATUS_IN_PROGRESS,
                        changed_at=in_prog_at,
                        changed_by="MECHANIC",
                        notes="Commenced diagnostic and repair"
                    )
                )
                history_rows.append(
                    BookingStatusHistory(
                        booking=b,
                        previous_status=Booking.STATUS_IN_PROGRESS,
                        new_status=Booking.STATUS_COMPLETED,
                        changed_at=completed_at,
                        changed_by="MECHANIC",
                        notes="Service completed and tested"
                    )
                )

            if cancelled_at:
                history_rows.append(
                    BookingStatusHistory(
                        booking=b,
                        previous_status=Booking.STATUS_PENDING if not assigned_at else Booking.STATUS_ASSIGNED,
                        new_status=Booking.STATUS_CANCELLED,
                        changed_at=cancelled_at,
                        changed_by="CUSTOMER",
                        notes="Customer cancelled appointment"
                    )
                )

            BookingStatusHistory.objects.bulk_create(history_rows)
            bookings_created += 1

        self.stdout.write(f"Successfully generated {bookings_created} historical bookings.")

    def create_live_attention_scenarios(self, customers, vehicles, mechanics, services):
        """
        Creates 4 deliberate live attention scenario fixtures:
        1. CRITICAL: 1 PENDING booking created 18 min ago (unassigned > 15m)
        2. HIGH: 2 ASSIGNED bookings assigned 12 & 14 min ago (delayed dispatch > 10m)
        3. WARNING (Delayed): 2 ON_THE_WAY bookings with passed ETA and arrived_at is NULL
        4. WARNING (Overloaded): 1 mechanic with >= 4 active bookings
        """
        self.stdout.write("Generating deliberate live attention scenarios...")
        now = timezone.now()

        # 1. CRITICAL: PENDING unassigned for 18m
        cust1 = customers[0]
        veh1 = [v for v in vehicles if v.customer_id == cust1.id][0]
        srv1 = services[0]
        created_1 = now - timedelta(minutes=18)

        b_crit = Booking.objects.create(
            booking_number="BK-CRIT-101",
            customer=cust1,
            vehicle=veh1,
            mechanic=None,
            service_category=srv1,
            status=Booking.STATUS_PENDING,
            amount=srv1.base_price,
            is_demo_scenario=True,
        )
        Booking.objects.filter(id=b_crit.id).update(created_at=created_1)
        BookingStatusHistory.objects.create(
            booking=b_crit,
            previous_status="CREATED",
            new_status=Booking.STATUS_PENDING,
            changed_at=created_1,
            changed_by="CUSTOMER",
            notes="Customer created emergency roadside request"
        )

        # 2. HIGH: 2 ASSIGNED bookings stuck for 12 & 14 minutes
        cust2 = customers[1]
        veh2 = [v for v in vehicles if v.customer_id == cust2.id][0]
        srv2 = services[1]
        mech2 = mechanics[1]
        created_2 = now - timedelta(minutes=22)
        assigned_2 = now - timedelta(minutes=14)

        b_high1 = Booking.objects.create(
            booking_number="BK-HIGH-201",
            customer=cust2,
            vehicle=veh2,
            mechanic=mech2,
            service_category=srv2,
            status=Booking.STATUS_ASSIGNED,
            amount=srv2.base_price,
            is_demo_scenario=True,
            assigned_at=assigned_2,
        )
        Booking.objects.filter(id=b_high1.id).update(created_at=created_2)
        BookingStatusHistory.objects.bulk_create([
            BookingStatusHistory(booking=b_high1, previous_status="CREATED", new_status=Booking.STATUS_PENDING, changed_at=created_2, changed_by="CUSTOMER"),
            BookingStatusHistory(booking=b_high1, previous_status=Booking.STATUS_PENDING, new_status=Booking.STATUS_ASSIGNED, changed_at=assigned_2, changed_by="DISPATCH", notes=f"Assigned to {mech2.name}")
        ])

        cust3 = customers[2]
        veh3 = [v for v in vehicles if v.customer_id == cust3.id][0]
        srv3 = services[2]
        mech3 = mechanics[2]
        created_3 = now - timedelta(minutes=20)
        assigned_3 = now - timedelta(minutes=12)

        b_high2 = Booking.objects.create(
            booking_number="BK-HIGH-202",
            customer=cust3,
            vehicle=veh3,
            mechanic=mech3,
            service_category=srv3,
            status=Booking.STATUS_ASSIGNED,
            amount=srv3.base_price,
            is_demo_scenario=True,
            assigned_at=assigned_3,
        )
        Booking.objects.filter(id=b_high2.id).update(created_at=created_3)
        BookingStatusHistory.objects.bulk_create([
            BookingStatusHistory(booking=b_high2, previous_status="CREATED", new_status=Booking.STATUS_PENDING, changed_at=created_3, changed_by="CUSTOMER"),
            BookingStatusHistory(booking=b_high2, previous_status=Booking.STATUS_PENDING, new_status=Booking.STATUS_ASSIGNED, changed_at=assigned_3, changed_by="DISPATCH", notes=f"Assigned to {mech3.name}")
        ])

        # 3. WARNING: 2 ON_THE_WAY bookings with passed ETA
        cust4 = customers[3]
        veh4 = [v for v in vehicles if v.customer_id == cust4.id][0]
        srv4 = services[3]
        mech4 = mechanics[3]
        created_4 = now - timedelta(minutes=45)
        assigned_4 = now - timedelta(minutes=40)
        started_4 = now - timedelta(minutes=35)
        eta_4 = now - timedelta(minutes=10) # 10 min overdue

        b_warn1 = Booking.objects.create(
            booking_number="BK-WARN-301",
            customer=cust4,
            vehicle=veh4,
            mechanic=mech4,
            service_category=srv4,
            status=Booking.STATUS_ON_THE_WAY,
            amount=srv4.base_price,
            is_demo_scenario=True,
            assigned_at=assigned_4,
            started_at=started_4,
            estimated_arrival_at=eta_4,
            arrived_at=None,
        )
        Booking.objects.filter(id=b_warn1.id).update(created_at=created_4)
        BookingStatusHistory.objects.bulk_create([
            BookingStatusHistory(booking=b_warn1, previous_status="CREATED", new_status=Booking.STATUS_PENDING, changed_at=created_4, changed_by="CUSTOMER"),
            BookingStatusHistory(booking=b_warn1, previous_status=Booking.STATUS_PENDING, new_status=Booking.STATUS_ASSIGNED, changed_at=assigned_4, changed_by="DISPATCH"),
            BookingStatusHistory(booking=b_warn1, previous_status=Booking.STATUS_ASSIGNED, new_status=Booking.STATUS_ON_THE_WAY, changed_at=started_4, changed_by="MECHANIC", notes="En route in traffic")
        ])

        cust5 = customers[4]
        veh5 = [v for v in vehicles if v.customer_id == cust5.id][0]
        srv5 = services[4]
        mech5 = mechanics[4]
        created_5 = now - timedelta(minutes=40)
        assigned_5 = now - timedelta(minutes=35)
        started_5 = now - timedelta(minutes=30)
        eta_5 = now - timedelta(minutes=5) # 5 min overdue

        b_warn2 = Booking.objects.create(
            booking_number="BK-WARN-302",
            customer=cust5,
            vehicle=veh5,
            mechanic=mech5,
            service_category=srv5,
            status=Booking.STATUS_ON_THE_WAY,
            amount=srv5.base_price,
            is_demo_scenario=True,
            assigned_at=assigned_5,
            started_at=started_5,
            estimated_arrival_at=eta_5,
            arrived_at=None,
        )
        Booking.objects.filter(id=b_warn2.id).update(created_at=created_5)
        BookingStatusHistory.objects.bulk_create([
            BookingStatusHistory(booking=b_warn2, previous_status="CREATED", new_status=Booking.STATUS_PENDING, changed_at=created_5, changed_by="CUSTOMER"),
            BookingStatusHistory(booking=b_warn2, previous_status=Booking.STATUS_PENDING, new_status=Booking.STATUS_ASSIGNED, changed_at=assigned_5, changed_by="DISPATCH"),
            BookingStatusHistory(booking=b_warn2, previous_status=Booking.STATUS_ASSIGNED, new_status=Booking.STATUS_ON_THE_WAY, changed_at=started_5, changed_by="MECHANIC")
        ])

        # 4. WARNING: Overloaded mechanic with 4 active bookings
        overloaded_mech = mechanics[0]
        for j in range(4):
            cust_j = customers[5 + j]
            veh_j = [v for v in vehicles if v.customer_id == cust_j.id][0]
            service_item = services[j % len(services)]
            b_load = Booking.objects.create(
                booking_number=f"BK-LOAD-40{j+1}",
                customer=cust_j,
                vehicle=veh_j,
                mechanic=overloaded_mech,
                service_category=service_item,
                status=Booking.STATUS_ASSIGNED if j < 2 else Booking.STATUS_IN_PROGRESS,
                amount=service_item.base_price,
                is_demo_scenario=True,
                assigned_at=now - timedelta(minutes=20 + j * 5),
                started_at=now - timedelta(minutes=15) if j >= 2 else None,
                arrived_at=now - timedelta(minutes=10) if j >= 2 else None,
            )
            Booking.objects.filter(id=b_load.id).update(created_at=now - timedelta(minutes=30 + j * 5))

        self.stdout.write("Created all deliberate live attention scenario fixtures.")
