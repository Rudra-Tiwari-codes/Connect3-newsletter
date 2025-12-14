import nodemailer from 'nodemailer';
import { supabase, User, RankedEvent } from './supabase';
import { EmailTemplateService } from './email-template';

// Gmail credentials are optional - will only error when actually sending
const GMAIL_CONFIGURED = !!(process.env.GMAIL_USER && process.env.GMAIL_APP_PASSWORD);

// Create reusable transporter for Gmail SMTP (only if configured)
const transporter = GMAIL_CONFIGURED
  ? nodemailer.createTransport({
    service: 'gmail',
    auth: {
      user: process.env.GMAIL_USER,
      pass: process.env.GMAIL_APP_PASSWORD,
    },
  })
  : null;

const FROM_EMAIL = process.env.GMAIL_FROM_EMAIL || process.env.GMAIL_USER || 'noreply@example.com';
const FEEDBACK_URL = process.env.NEXT_PUBLIC_APP_URL
  ? `${process.env.NEXT_PUBLIC_APP_URL}/api/feedback`
  : 'http://localhost:3000/api/feedback';

export class EmailDeliveryService {
  private templateService: EmailTemplateService;

  constructor() {
    this.templateService = new EmailTemplateService();
  }

  /**
   * Send newsletters to all users grouped by cluster
   */
  async sendNewsletters(rankedEventsByUser: Map<string, RankedEvent[]>): Promise<void> {
    let successCount = 0;
    let failureCount = 0;

    for (const [userId, events] of rankedEventsByUser.entries()) {
      try {
        await this.sendPersonalizedEmail(userId, events);
        successCount++;

        // Rate limiting: wait 100ms between sends
        await this.sleep(100);
      } catch (error) {
        console.error(`Failed to send email to user ${userId}:`, error);
        failureCount++;
      }
    }

    console.log(`Email delivery complete: ${successCount} sent, ${failureCount} failed`);
  }

  /**
   * Send a personalized email to a single user
   */
  async sendPersonalizedEmail(userId: string, events: RankedEvent[]): Promise<void> {
    // Fetch user data
    const { data: user, error: userError } = await supabase
      .from('users')
      .select('*')
      .eq('id', userId)
      .single();

    if (userError || !user) {
      throw new Error(`Failed to fetch user: ${userError?.message}`);
    }

    // Generate email HTML
    const htmlContent = this.templateService.generatePersonalizedEmail(user, events, FEEDBACK_URL);

    // Prepare email message
    const mailOptions = {
      from: FROM_EMAIL,
      to: user.email,
      subject: `Your Weekly Event Picks - ${events.length} Events Curated For You`,
      html: htmlContent,
    };

    try {
      // Send email via Gmail SMTP
      if (!transporter) {
        throw new Error('Gmail not configured. Set GMAIL_USER and GMAIL_APP_PASSWORD to send emails.');
      }
      await transporter.sendMail(mailOptions);

      // Log success
      const { error: logError } = await supabase.from('email_logs').insert({
        user_id: userId,
        status: 'sent',
        sent_at: new Date().toISOString(),
      });

      if (logError) {
        console.error(`Failed to log email success for user ${userId}:`, logError);
        // Don't throw - email was sent successfully, just logging failed
      }

      console.log(`Email sent successfully to ${user.email}`);
    } catch (error: any) {
      // Log failure
      const { error: logError } = await supabase.from('email_logs').insert({
        user_id: userId,
        status: 'failed',
        error_message: error.message || 'Unknown error',
        sent_at: new Date().toISOString(),
      });

      if (logError) {
        console.error(`Failed to log email failure for user ${userId}:`, logError);
        // Log to console as fallback
        console.error(`Email send failed for user ${userId}:`, error.message || 'Unknown error');
      }

      throw error;
    }
  }

  /**
   * Send test email
   */
  async sendTestEmail(toEmail: string): Promise<void> {
    const mailOptions = {
      from: FROM_EMAIL,
      to: toEmail,
      subject: 'Test Email - Event Newsletter System',
      html: '<h1>Test Email</h1><p>This is a test email from the Event Newsletter System.</p>',
    };

    if (!transporter) {
      throw new Error('Gmail not configured. Set GMAIL_USER and GMAIL_APP_PASSWORD to send emails.');
    }
    await transporter.sendMail(mailOptions);
    console.log(`Test email sent to ${toEmail}`);
  }

  /**
   * Helper to sleep for rate limiting
   */
  private sleep(ms: number): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }
}
