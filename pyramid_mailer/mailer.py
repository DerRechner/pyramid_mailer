import smtplib

from repoze.sendmail.mailer import SMTPMailer
from repoze.sendmail.delivery import DirectMailDelivery
from repoze.sendmail.delivery import QueuedMailDelivery


class DummyMailer(object):

    """
    Dummy mailing instance
    Used for example in unit tests.

    Keeps all sent messages internally in list as **outbox** property.
    Queued messages are instead added to **queue** property.
    """

    def __init__(self):
        self.outbox = []
        self.queue = []

    def send(self, message):    
        """
        Mocks sending a direct message. The message is added to the **outbox**
        list.

        :param message: a **Message** instance.
        """
        self.outbox.append(message)

    def send_to_queue(self, message):
        """
        Mocks sending to a maildir queue. The message is added to the **queue**
        list.

        :param message: a **Message** instance.
        """
        self.queue.append(message)


class SMTP_SSLMailer(SMTPMailer):
    """
    Subclass of SMTPMailer enabling SSL.
    """

    smtp = smtplib.SMTP_SSL

    def __init__(self, *args, **kwargs):
        self.keyfile = kwargs.pop('keyfile', None)
        self.certfile = kwargs.pop('certfile', None)

        super(SMTP_SSLMailer, self).__init__(*args, **kwargs)

    def smtp_factory(self):

        connection = self.smtp(self.hostname, str(self.port),
                               keyfile=self.keyfile,
                               certfile=self.certfile)

        connection.set_debuglevel(self.debug_smtp)
        return connection


class Mailer(object):
    """
    Manages sending of email messages.

    :param settings: a settings dict. See documentation on the 
                      individual settings required.
    """

    def __init__(self, 
                 host='localhost', 
                 port=25, 
                 username=None,
                 password=None, 
                 tls=False,
                 ssl=False,
                 keyfile=None,
                 certfile=None,
                 queue_path=None,
                 default_sender=None,
                 debug=0):


        if ssl:

            smtp_mailer = SMTP_SSLMailer(hostname=host,
                                         port=port,
                                         username=username,
                                         password=password,
                                         no_tls=not(tls),
                                         force_tls=tls,
                                         debug_smtp=debug,
                                         keyfile=keyfile,
                                         certfile=certfile)

        else:

            smtp_mailer = SMTPMailer(hostname=host, 
                                     port=port, 
                                     username=username, 
                                     password=password, 
                                     no_tls=not(tls), 
                                     force_tls=tls, 
                                     debug_smtp=debug)

        self.direct_delivery = DirectMailDelivery(smtp_mailer)

        if queue_path:
            self.queue_delivery = QueuedMailDelivery(queue_path)
        else:
            self.queue_delivery = None

        self.default_sender = default_sender

    @classmethod
    def from_settings(cls, settings, prefix='mail.'):
        """
        Creates a new instance of **Message** from settings dict.

        :param settings: a settings dict-like
        :param prefix: prefix separating **pyramid_mailer** settings
        """

        settings = settings or {}

        kwarg_names = [prefix + k for k in (
                       'host', 'port', 'username',
                       'password', 'tls', 'ssl', 'keyfile', 
                       'certfile', 'queue_path', 'debug')]
        
        size = len(prefix)

        kwargs = dict(((k[size:], settings[k]) for k in settings.keys() if
                        k in kwarg_names))

        return cls(**kwargs)

    def send(self, message):
        """
        Sends a message immediately.

        :param message: a **Message** instance.
        """

        return self.direct_delivery.send(*self._message_args(message))
        
    def send_to_queue(self, message):
        """
        Adds a message to a maildir queue.
        
        In order to handle this, the setting **mail.queue_path** must be 
        provided and must point to a valid maildir.

        :param message: a **Message** instance.
        """

        if not self.queue_delivery:
            raise RuntimeError, "No queue_path provided"
    
        return self.queue_delivery.send(*self._message_args(message))

    def _message_args(self, message):

        message.sender = message.sender or self.default_sender

        return (message.sender, 
                message.recipients,
                message.to_message())

