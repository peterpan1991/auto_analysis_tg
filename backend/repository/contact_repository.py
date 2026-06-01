from sqlalchemy.orm import Session
from models import Contact
from typing import Optional, List

def get_contact_by_id(db: Session, contact_id: int) -> Optional[Contact]:
    return db.query(Contact).filter(Contact.id == contact_id).first()

def get_contacts_by_user(db: Session, user_id: int) -> List[Contact]:
    return db.query(Contact).filter(Contact.user_id == user_id).all()

def create_contact(db: Session, contact: Contact) -> Contact:
    db.add(contact)
    db.commit()
    db.refresh(contact)
    return contact

def update_contact(db: Session, contact: Contact) -> Contact:
    db.commit()
    db.refresh(contact)
    return contact

def delete_contact(db: Session, contact_id: int) -> Optional[Contact]:
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if contact:
        db.delete(contact)
        db.commit()
    return contact
