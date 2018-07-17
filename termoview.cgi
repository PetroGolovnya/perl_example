#!/usr/bin/perl
#termoview.cgi - показ архивных данных темепратуры окр. воздуха
use utf8;
use open qw(:std :utf8);
use strict;
use lib qw(/var/www/cgi-bin/libs);
use DBI;
use CGI qw(:standard);
use CGI::Carp qw(fatalsToBrowser);
use Template;
use Time::Piece;

my $today = (Time::Piece->new)->strftime("%d-%m-%Y");
my $yesterday = (Time::Piece->new - (24 * 3600))->strftime("%d-%m-%Y");
my $day_3 = (Time::Piece->new - (3 *24 * 3600))->strftime("%d-%m-%Y");
my $day_7 = (Time::Piece->new - (7 *24 * 3600))->strftime("%d-%m-%Y");
my $day_10 = (Time::Piece->new - (10 *24 * 3600))->strftime("%d-%m-%Y");

my $form = new CGI;
my $date_start = $form->param("date_start") ? $form->param("date_start") : $yesterday;
my $date_end = $form->param("date_end") ? $form->param("date_end") : $today;
my $act = $form->param("act") ? $form->param("act") : 'noprint';

my $dt_end = Time::Piece->strptime($date_end, "%d-%m-%Y") + 24 * 3600;
$dt_end = $dt_end->strftime("%d-%m-%Y");
my $dt_start = $date_start;

my $dbh = DBI->connect("dbi:ODBC:DSN=TEPLO", 'user', 'password') or die "Couldn't connect to database: " . DBI->errstr;
my $sth = $dbh->prepare("set dateformat dmy; SELECT AVG(air) as air from air where date >= ? and date < ?");
$sth->execute($dt_start, $dt_end);

my $period;
while(my @result = $sth->fetchrow()){
	$period = $result[0];
}

my %ds = ();
my %avg = ();

while ( Time::Piece->strptime($dt_start, "%d-%m-%Y") < Time::Piece->strptime($dt_end, "%d-%m-%Y") ) {        
    my $date = Time::Piece->strptime($dt_start, "%d-%m-%Y") + (24 * 3600);
    my $date = $date->strftime("%d-%m-%Y");	
	    
    $sth = $dbh->prepare("set dateformat dmy; SELECT date, FORMAT(air, 'N1') as air from air where date >= ? and date < ? order by date");
    $sth->execute($dt_start, $date);
    my $results = $sth->fetchall_arrayref(\{ 0 => 'date_p', 1 => 'air' });
    $ds{Time::Piece->strptime($dt_start, "%d-%m-%Y")->strftime("%s")} = $results; # хеш с ключом в виде даты в формате UNIX time

    $sth = $dbh->prepare("set dateformat dmy; SELECT AVG(air) as air from air where date >= ? and date < ?");
    $sth->execute($dt_start, $date);
    $results = $sth->fetchall_arrayref(\{ 0 => 'avg_air' });	
    $avg{Time::Piece->strptime($dt_start, "%d-%m-%Y")->strftime("%s")} = $results; # хеш с ключом в виде даты в формате UNIX time
		
    $dt_start = $date;		
}

$sth->finish();
$dbh->disconnect();

my %pack = ();

foreach my $key ( keys %ds ) {
    my @results = ();
    for my $i ( 0 .. 23 ) { 
	my $date_p = Time::Piece->strptime($key, "%s") + $i * 3600 + 7 * 3600;
	$date_p = $date_p->strftime("%Y-%m-%d %H:%M:%S.000");
        (my $p) = grep { $date_p eq $_->{'date_p'} } @{ $ds{$key} };	
        if ($p) {            		    
	    push @results, { date_p => $p->{'date_p'}, air => $p->{'air'} };
        }
        else {            
	    push @results, { date_p => $date_p, air => '--' };
        }
    }
    $pack{$key} = [ @results ];		
}

my $file = 'termoview.tt';

my $vars = {
        'rows' => \%pack,
	'avgs' => \%avg,
	'period' => $period,
	'date_start' => $date_start,
	'date_end' => $date_end,
	'today' => $today,
	'yesterday' => $yesterday,
	'day_3' => $day_3,
	'day_7' => $day_7,
	'day_10' => $day_10,
	'act' => $act,
};

my $template = Template->new({
    INCLUDE_PATH => 'templates',
    ENCODING => 'utf8',
    POST_CHOMP => 1,	
    STRICT => 1,		
});

$| = 1;

print "Content-type: text/html\n\n";
$template->process($file, $vars)
    || die "Template process failed: ", $template->error(), "\n";
