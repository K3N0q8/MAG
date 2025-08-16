<?php

// --- Data Models ---

class Family {
    public $id;
    public $family_name;
    public $head_of_household;
    public $contact_email;
    public $contact_phone;
    public $member_count;
    public $annual_fee;
    public $role;

    public function __construct($family_name, $head_of_household, $member_count, $contact_email = null, $contact_phone = null, $annual_fee = 0.0, $role = null, $id = null) {
        $this->id = $id;
        $this->family_name = $family_name;
        $this->head_of_household = $head_of_household;
        $this->contact_email = $contact_email;
        $this->contact_phone = $contact_phone;
        $this->member_count = $member_count;
        $this->annual_fee = $annual_fee;
        $this->role = $role;
    }
}

class Payment {
    public $id;
    public $family_id;
    public $amount;
    public $payment_date;
    public $status;

    public function __construct($family_id, $amount, $payment_date, $status, $id = null) {
        $this->id = $id;
        $this->family_id = $family_id;
        $this->amount = $amount;
        $this->payment_date = $payment_date;
        $this->status = $status;
    }
}

class Project {
    public $id;
    public $name;
    public $description;
    public $status;
    public $start_date;
    public $planned_cost;
    public $current_cost;

    public function __construct($name, $status, $description = null, $start_date = null, $planned_cost = 0.0, $current_cost = 0.0, $id = null) {
        $this->id = $id;
        $this->name = $name;
        $this->description = $description;
        $this->status = $status;
        $this->start_date = $start_date;
        $this->planned_cost = $planned_cost;
        $this->current_cost = $current_cost;
    }
}

class Resource {
    public $id;
    public $name;
    public $type;
    public $quantity;
    public $assigned_family_id;

    public function __construct($name, $type, $quantity, $assigned_family_id = null, $id = null) {
        $this->id = $id;
        $this->name = $name;
        $this->type = $type;
        $this->quantity = $quantity;
        $this->assigned_family_id = $assigned_family_id;
    }
}

class Event {
    public $id;
    public $name;
    public $description;
    public $start_date;
    public $end_date;

    public function __construct($name, $start_date, $end_date, $description = null, $id = null) {
        $this->id = $id;
        $this->name = $name;
        $this->description = $description;
        $this->start_date = $start_date;
        $this->end_date = $end_date;
    }
}

class VillageManagement {
    private $pdo;

    public function __construct($dbFile) {
        try {
            $this->pdo = new PDO('sqlite:' . $dbFile);
            $this->pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
        } catch (PDOException $e) {
            die("Connection failed: " . $e->getMessage());
        }
    }

    public function createTables() {
        $commands = [
            'CREATE TABLE IF NOT EXISTS families (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                family_name TEXT NOT NULL,
                head_of_household TEXT NOT NULL,
                contact_email TEXT,
                contact_phone TEXT,
                member_count INTEGER NOT NULL,
                annual_fee REAL,
                role TEXT
            )',
            'CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                family_id INTEGER NOT NULL,
                amount REAL NOT NULL,
                payment_date TEXT NOT NULL,
                status TEXT NOT NULL,
                FOREIGN KEY (family_id) REFERENCES families (id)
            )',
            'CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                status TEXT NOT NULL,
                start_date TEXT,
                planned_cost REAL,
                current_cost REAL
            )',
            'CREATE TABLE IF NOT EXISTS resources (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                assigned_family_id INTEGER,
                FOREIGN KEY (assigned_family_id) REFERENCES families (id)
            )',
            'CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                start_date TEXT NOT NULL,
                end_date TEXT NOT NULL
            )'
        ];

        try {
            foreach ($commands as $command) {
                $this->pdo->exec($command);
            }
            echo "Tables created successfully.\n";
        } catch (PDOException $e) {
            die("Table creation failed: " . $e->getMessage());
        }
    }

    public function seedDatabase() {
        try {
            // Check if families table is empty before seeding
            $stmt = $this->pdo->query('SELECT COUNT(*) FROM families');
            if ($stmt->fetchColumn() > 0) {
                echo "Database has already been seeded.\n";
                return;
            }

            // Sample Data
            $families = [
                new Family('Petrović', 'Pera', 4, 'pera@example.com', '111-222', 50.0, 'Član'),
                new Family('Jovanović', 'Jova', 3, 'jova@example.com', '333-444', 50.0, 'Odbornik'),
                new Family('Marković', 'Marko', 5, 'marko@example.com', '555-666', 75.0, 'Član'),
            ];

            $projects = [
                new Project('Popravka seoskog puta', 'Trenutni', 'Asfaltiranje glavnog puta kroz selo.', '2024-07-01', 5000.0, 1500.0),
                new Project('Organizacija seoske slave', 'Planiran', 'Priprema za proslavu Sv. Ilije.', '2024-08-02', 1000.0, 0.0),
                new Project('Čišćenje rečnog korita', 'Završen', 'Uklanjanje otpada iz reke.', '2024-05-15', 300.0, 300.0),
            ];

            $payments = [
                new Payment(1, 50.0, '2024-01-15', 'Plaćeno'),
                new Payment(2, 25.0, '2024-06-01', 'Kasni'),
                new Payment(3, 75.0, '2024-02-20', 'Plaćeno'),
                new Payment(2, 25.0, '2024-07-01', 'Dug'),
            ];

            $resources = [
                new Resource('Traktor', 'Vozilo', 1, 2), // Assigned to Jovanović
                new Resource('Kosačica', 'Alat', 2),
                new Resource('Prikolica', 'Vozilo', 1),
            ];

            $events = [
                new Event('Seoska slava - Sv. Ilija', 'Godišnja proslava seoske slave.', '2024-08-02 10:00', '2024-08-02 22:00'),
                new Event('Radna akcija - čišćenje', 'Okupljanje za čišćenje centra sela.', '2024-09-01 09:00', '2024-09-01 14:00'),
            ];

            // Insert Families
            $stmt = $this->pdo->prepare('INSERT INTO families (family_name, head_of_household, member_count, contact_email, contact_phone, annual_fee, role) VALUES (?, ?, ?, ?, ?, ?, ?)');
            foreach ($families as $family) {
                $stmt->execute([$family->family_name, $family->head_of_household, $family->member_count, $family->contact_email, $family->contact_phone, $family->annual_fee, $family->role]);
            }

            // Insert Projects
            $stmt = $this->pdo->prepare('INSERT INTO projects (name, status, description, start_date, planned_cost, current_cost) VALUES (?, ?, ?, ?, ?, ?)');
            foreach ($projects as $project) {
                $stmt->execute([$project->name, $project->status, $project->description, $project->start_date, $project->planned_cost, $project->current_cost]);
            }

            // Insert Payments
            $stmt = $this->pdo->prepare('INSERT INTO payments (family_id, amount, payment_date, status) VALUES (?, ?, ?, ?)');
            foreach ($payments as $payment) {
                $stmt->execute([$payment->family_id, $payment->amount, $payment->payment_date, $payment->status]);
            }

            // Insert Resources
            $stmt = $this->pdo->prepare('INSERT INTO resources (name, type, quantity, assigned_family_id) VALUES (?, ?, ?, ?)');
            foreach ($resources as $resource) {
                $stmt->execute([$resource->name, $resource->type, $resource->quantity, $resource->assigned_family_id]);
            }

            // Insert Events
            $stmt = $this->pdo->prepare('INSERT INTO events (name, description, start_date, end_date) VALUES (?, ?, ?, ?)');
            foreach ($events as $event) {
                $stmt->execute([$event->name, $event->description, $event->start_date, $event->end_date]);
            }

            echo "Database seeded successfully.\n";

        } catch (PDOException $e) {
            die("Database seeding failed: " . $e->getMessage());
        }
    }
}

// Main execution
if (php_sapi_name() === 'cli') {
    $dbFile = 'village.db';
    $vm = new VillageManagement($dbFile);
    $vm->createTables();
    $vm->seedDatabase();
    echo "Database '$dbFile' and its tables have been initialized and seeded.\n";
}

?>
