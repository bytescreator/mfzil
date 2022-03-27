import os
import json
import time

import logging
logging.basicConfig(level=10)
logger = logging.getLogger('zilscheduler')

UTCZone = 3
POLL_PERIOD = 1

import marshmallow
import vlc

ACCEPTED_DAYS = ['pazartesi', 'sali', 'carsamba', 'persembe', 'cuma', 'cumartesi', 'pazar']
ALLOWABLE_SLEEP_DRIFT = 5

class TimeSchema(marshmallow.Schema):
    def __check_ring_sound_location(data):
        if not os.path.exists(data):
            raise ValueError('Zil Sesi Bulunamadı.')

    def __check_days(day):
        if not day in ACCEPTED_DAYS:
            raise marshmallow.exceptions.ValidationError('Konfigürasyon hatası, bilinmeyen gün.')

    def __check_time(time):
        x = time.split(':')
        if len(x) != 2:
            raise marshmallow.exceptions.ValidationError('Konfigürasyon hatası. Saatler ile ilgili format hatası var.')

        try:
            int(x[0])
            int(x[1])

        except TypeError:
            raise marshmallow.exceptions.ValidationError('Konfigürasyon ile ilgili hata, saatler tamsayı değil.')

        if (int(x[0]) < 0) or (int(x[0]) > 23):
            raise marshmallow.exceptions.ValidationError('Konfigürasyon hatası. Saatler ile ilgili format hatası var.')

        if (int(x[0]) < 0) or (int(x[1]) > 59):
            raise marshmallow.exceptions.ValidationError('Konfigürasyon hatası. Saatler ile ilgili format hatası var.')

    @marshmallow.post_load
    def last_check(self, data, **kwargs):
        for index, time in enumerate(data['times']):
            x=time.split(':')
            data['times'][index] = int(x[0])*3600+int(x[1])*60

            if data['times'].count(data['times'][index]) > 1:
                raise marshmallow.exceptions.ValidationError('Bir gün için birden fazla aynı saat var.')


        for day in data['forDays']:
            if data['forDays'].count(day) > 1:
                raise marshmallow.exceptions.ValidationError('Aynı gün için birden fazla girdi.')

        return data

    forDays = marshmallow.fields.List(marshmallow.fields.Str(validate=__check_days, unique=True), required=True)
    SoundFile = marshmallow.fields.Str(validate=__check_ring_sound_location, required=True)
    times = marshmallow.fields.List(marshmallow.fields.Str(validate=__check_time, unique=True), required=True)
    description = marshmallow.fields.Str()

class JSONConfigSchema(marshmallow.Schema):
    RingTimes = marshmallow.fields.List(marshmallow.fields.Nested(TimeSchema), required=True)

class Ringer:
    def __init__(self, RingTimes):
        self.week_second_at_start = self.seconds_since_weekstart()+3600*UTCZone
        logger.info("UTC Zone'u : %s" % UTCZone)
        logger.info("Pazartesiden beri geçen saniye: %s" % self.week_second_at_start)

        self.RingTimes = RingTimes

        logger.debug("Kullanılan konfigürasyona göre:\n\n")
        for entry in self.RingTimes:
            logger.debug("Günler: %s " % " ".join(entry["forDays"]))
            logger.debug("Zil Sesi: %s" % entry["SoundFile"])
            logger.debug("Açıklama: %s" % entry.get("description"))

            logger.debug("Zamanlar : \n\n%s\n\n" % "  \n".join(["{}. Girdi | {}:{}".format(_index+1, u//3600, u%3600//60) for _index, u in enumerate(entry["times"])]))

        logger.info("VLC MediaPlayer Oluşuruluyor...")
        self.player = vlc.MediaPlayer()


        logger.info("Çalma döngüsü başlatılıyor...")
        while True:
            self.sleeper_loop()

    @staticmethod
    def seconds_since_weekstart():
        return ((time.time()+259200+UTCZone*3600) % (604800))

    @staticmethod
    def __precise_sleep(sec):
        if sec < 0:
            return

        a = time.time()
        while((time.time() - a) <= sec):
            time.sleep(POLL_PERIOD)

        return a

    def calc_ring_intervals(self):
        self.week_second_at_start = self.seconds_since_weekstart()
        secs = {}
        for entry in self.RingTimes:
            for day in entry['forDays']:
                day_offset = ACCEPTED_DAYS.index(day)*86400
                for i in entry['times'] :
                    if (day_offset+i) > self.week_second_at_start:
                        if (day_offset+i) in secs:
                            logger.critical("Çift zaman bulundu konfigürasyonu kontrol ediniz.")
                            raise ValueError("Çift zaman bulundu konfigürasyonu kontrol ediniz.")
                        secs.update({day_offset+i: entry["SoundFile"]})

        return secs

    def sleeper_loop(self):
        x=self.calc_ring_intervals()
        logger.debug("Interval listesi: %s" % x)

        times=list(x.keys())
        times.sort()

        for t in times:
            logger.info(" %s:%s.%s için bekleniyor... Çalınacak zil: %s" % (ACCEPTED_DAYS[(t//86400)], (t%86400//3600), (t%3600)//60, x[t]))
            try:
                target_sleep = t - self.seconds_since_weekstart()
                start_time = self.__precise_sleep(target_sleep)
            except KeyboardInterrupt:
                if input("Zil pas geçilsin mi (Y/N) ?").upper() == "Y":
                    self.player.stop()
                    logger.info(" %s:%s.%s pas geçildi." % (ACCEPTED_DAYS[(t//86400)], (t%86400//3600), (t%3600)//60))
                    continue
                else:
                    exit()

            if abs(time.time() - (start_time+target_sleep)) > ALLOWABLE_SLEEP_DRIFT:
                logger.warning("Muhtemel uyku nedenli zaman kayması çok fazla olduğundan zil çalınmayacak.")
                continue

            if not self.player.is_playing():
                self.player.stop()
                self.player.set_mrl(x[t])
                self.player.play()

            else:
                logger.warning("Zil bitmeden başka bir zil çalınmaya çalışıldı, pas geçiliyor...")

        logger.info("Hafta Başlangıcı Bekleniyor...")

        try:
            self.__precise_sleep((604800 - self.seconds_since_weekstart()))
        except KeyboardInterrupt:
            logger.info("Program Durduruldu.")
            exit()

        logger.info("----------Haftalık yeniden başlatma-----------")


with open('config.json','r', encoding="utf-8") as f:
    logger.info("Konfigürasyon Yükleniyor...")
    config = JSONConfigSchema().loads(''.join([line for line in f if not line.replace(' ','').replace('\t','').startswith('//')]))

    logger.info("Ringer Başlatılıyor...")
    x=Ringer(**config)
