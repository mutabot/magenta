sudo cp dupervisord /etc/rc.d/init.d/
sudo chmod +x /etc/rc.d/init.d/supervisord
sudo chkconfig --add supervisord
sudo chkconfig supervisord on
sudo service supervisord start