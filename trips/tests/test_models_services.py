def test_create_trip_is_atomic(self): # Si la participation échoue tout échoue et rien est créé.
    before = Trip.objects.count()
    with mock.patch("trips.services.Participation.objects.create",
        side_effect=RuntimeError("panne")):
        with self.assertRaises(RuntimeError):
            services.create_trip(
                owner=self.dave, title="Asie", start_date=date(2027, 9, 1), end_date=date(2027, 9, 10)
            )
    self.assertEqual(Trip.objects.count(), before)